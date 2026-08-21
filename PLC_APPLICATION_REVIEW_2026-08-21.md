# PLC Uygulama Dalı İncelemesi — 21 Ağustos 2026

İncelenen dal: `origin/motion-steering-control`

İncelenen son commit: `2c4116d` (`Clarify Orin auto steering safety gate`)

Ana wire otoritesi:
`rover-core-ros2/agent/local-metric-map@caba72c7cce4fdc64328caa1b586c3be68077b23`

Bu raporu hazırlayan Ana Proje Codex'i yalnız uyumluluk incelemesi ve canlı
salt-okunur test yapmıştır. PLC SCL/Python uygulama kodu değiştirilmemiş,
PLC'ye download yapılmamış ve FC16 yazma testi çalıştırılmamıştır.

## 1. Canlı VM–PLC ağ ve FC03 sonucu

Doğrulanan topoloji:

| Uç | Adres | Sonuç |
|---|---|---|
| VM PLC adaptörü | `192.168.2.10/24`, `enp0s9` | UP |
| VM SSH adaptörü | `192.168.144.10/24`, `enp0s8` | korundu |
| PLC | `192.168.2.100/24` | ping 3/3 |
| PLC Modbus TCP | `192.168.2.100:502` | açık |
| ESP gateway | `192.168.2.166/24` | ping 2/2, TCP/502 açık |

Aynı kalıcı TCP oturumunda üç örnek boyunca PLC state ve G16 status blokları
FC03 ile okunup ana ROS codec'iyle doğrulandı:

- `PLC_TO_ORIN_STATE`: magic `0x5253`, protocol `1.1`, begin/end eşit, CRC
  doğru, sequence her örnekte ilerledi;
- `G16_STATUS`: magic `0x5247`, protocol `1.1`, begin/end eşit, CRC doğru,
  sequence her örnekte ilerledi.

Son canlı typed değer özeti:

| Alan | Değer |
|---|---:|
| `plc_session_id` | `3` |
| `operational_state` | `3` (`MANUAL`) |
| `active_authority` | `1` (`MANUAL`) |
| `status_flags` | `0x0502` |
| `fault_bits` / `interlock_bits` | `0` / `0` |
| `g16_summary_flags` | `0x0069` |
| `safety_summary_flags` | `0x0002` |
| `decoder_session_id` | `1152154963` |
| `sbus_flags` | `0x0009` |
| `channel_count` / mask | `16` / `0xFFFF` |

`PLC_DIAGNOSTICS` offset `192` ve `ACTIVE_CONFIG` offset `256` blokları
tamamen sıfır okundu. Bu, uygulama dalındaki belgelenmiş mevcut sınırla
uyumludur; iki publisher henüz tamamlanmamıştır.

ESP portu açıldı ancak PLC'nin aktif poll oturumu sırasında VM'den doğrudan
ESP FC03 uygulama cevabı alınamadı. PLC–ESP canlı akışı PLC'nin ilerleyen G16
snapshot'ı üzerinden doğrulandı; doğrudan ESP testi ayrı bakım penceresinde
tekrarlanmalıdır.

## 2. [P1] Orin snapshot sequence progression uygulanmıyor

`exported/blocks/FB_OrinCommandSnapshotValidator.scl`, begin/end eşitliğini
kontrol ediyor fakat kabul edilen son `begin_sequence` değerini saklayıp
modulo-2^32 yarım-aralık kuralıyla yeni/duplicate/backward kontrolü yapmıyor.
Yalnız payload içindeki `command_sequence` ilerlemesi izleniyor.

Ana sözleşmede snapshot sequence ile command sequence ayrı sayaçlardır ve
birinin ilerlemesi diğerinin stale/rollback durumunu gizleyemez. Aynı veya
geriye giden snapshot sequence yeni kabul sayılamaz.

Gerekli düzeltme:

- son kabul edilen snapshot sequence ve “have accepted” state'i tut;
- session değişiminde sequence baseline'ını sıfırla;
- `delta = candidate - previous` için yalnız `0 < delta < 0x80000000`
  değerini yeni kabul et;
- duplicate değeri freshness resetlemeden beklet veya açıkça reject et;
- backward/half-range değerini `SEQUENCE_NOT_ADVANCING` yap;
- duplicate, backward ve `0xFFFFFFFF -> 0` wrap testlerini ekle.

## 3. [P1] Heartbeat ve G16 frame counter gerilemesi ilerleme sayılıyor

Orin validator heartbeat'i `Heartbeat <> LastHeartbeat` olduğunda ilerlemiş
sayıyor. G16 validator da `SbusFrameCounter <> LastObservedFrameCounter`
olduğunda frame freshness zamanlayıcısını sıfırlıyor. Bu yaklaşım geriye giden
veya iki eski değer arasında değişen sayaçların freshness üretmesine izin
verebilir.

Gerekli düzeltme:

- heartbeat ve SBUS frame counter için de modulo-2^32 yarım-aralık
  karşılaştırması kullan;
- yalnız `0 < delta < 0x80000000` ilerlemedir;
- aynı değer timer'ı sıfırlamaz;
- backward değer invalid/reject/counter anomaly tanısı üretir;
- wrap, duplicate, backward ve eski değerler arasında toggle testleri eklenir.

ESP `sbus_frame_counter` her PLC poll'unda değişmek zorunda değildir; bu bulgu
timeout penceresini daraltma talebi değildir.

## 4. [P1] ROS istemci bağlantı modeli gerçek MB_SERVER ile uyumsuz

Canlı testte ilk FC03 bağlantısı kapatıldıktan hemen sonra açılan ikinci TCP
bağlantısı PLC tarafından reddedildi. Aynı kalıcı TCP bağlantısı içinde state
ve G16 bloklarına ardışık FC03 istekleri ise kararlı biçimde geçti.

Ana ROS `ModbusTcpClient` şu anda her `_request()` çağrısında yeni
`socket.create_connection()` açıp isteğin sonunda kapatıyor. Ayrıca command ve
state adapter düğümleri ayrı istemci nesneleri kullanıyor. PLC tarafındaki tek
`MB_SERVER` instance'ı/portu ile bu model:

- hızlı reconnect sırasında `connection refused`;
- uzun command stream açıkken state okuyucunun bağlanamaması;
- iki ROS düğümünün tek PLC oturumu için yarışması

riski taşır.

Gerçek Orin entegrasyonundan önce tek sahipli, kalıcı bir Modbus session
tasarlanmalıdır. Önerilen yön:

1. Tek ROS PLC transport düğümü/worker TCP oturumunun sahibi olur.
2. Aynı oturumda periyodik FC16 command ve sıralı FC03 state/G16/diagnostics/
   config isteklerini zamanlar.
3. Reconnect backoff, transaction ID, timeout ve health tek yerde tutulur.
4. Command kabulü yalnız FC16 ACK değil, PLC accepted session/sequence geri
   bildirimiyle belirlenir.

PLC tarafında ikinci server/port açmak, tek Orin command writer ve atomik raw
DB sahipliğini karmaşıklaştıracağından ilk çözüm olarak önerilmez.

## 5. [P2] FC03 bench scripti magic ve reserved-zero kontrol etmiyor

`scripts/test_orin_modbus_fc03.py`, 64-register cevapta version/length,
begin/end ve CRC kontrol ediyor; başlangıç offsetine göre beklenen magic'i ve
ilgili bloğun reserved alanlarını kontrol etmiyor. Yanlış blok türü veya
non-zero reserved payload bu scriptte başarılı görünebilir.

Script en az şu eşlemeyi doğrulamalıdır:

| Start | Magic | Reserved |
|---:|---:|---|
| 64 | `0x5253` | local `48..59` |
| 128 | `0x5247` | local `50..59` |
| 192 | `0x5244` | local `50..59` |
| 256 | `0x5246` | local `47..59` |

## 6. [P2] Session re-arm aynı-scan yarışı

Orin validator `RearmRising` değerini scan başında hesaplıyor, ardından aynı
scan içinde ilk yeni session snapshot'ını görüyor ve scan sonunda
`HaveSeenSessionState` üzerinden re-arm'ı kabul edebiliyor. Re-arm darbesi ilk
snapshot ile tesadüfen aynı scan'e denk gelirse “session görüldükten sonra
yeni yükselen kenar” koşulu kesin olarak kanıtlanmıyor.

Re-arm yalnız önceki scan'den beri pending olduğu bilinen session kimliğine
bağlanmalı; pulse ile pending-session eşleşmesi state olarak tutulmalıdır.

## 7. Tamamlanması gereken bilinen kapılar

Aşağıdakiler uygulama belgelerinde de açıkça eksik ve canlı okumayla teyit
edildi:

- `PLC_DIAGNOSTICS` typed model/encoder/publisher;
- `ACTIVE_CONFIG` typed model/encoder/publisher ve gerçek validity bitleri;
- PLC-owned output write-violation detection ve aynı-scan republish;
- uygulama dalının `agent/plc-contract-decisions@7e16a9b` ile kontrollü
  birleştirilmesi;
- AUTO validated command -> steering supervisor bağlantısı;
- AUTO için active-config, localization/navigation/geofence/mission ve
  safety authority guard'larının birlikte tamamlanması.

AUTO'nun `RejectReason=11` ile kapalı tutulması bu aşamada doğru ve güvenli
davranıştır. Yukarıdaki kapılar kapanmadan AUTO veya gerçek Orin direksiyon
hareketi açılmaz.

## 8. Önerilen sonraki sıra

1. Bölüm 2–4'teki üç P1 bulguyu kapat.
2. Yeni sequence/counter ve persistent-session test kanıtlarını ekle.
3. Sözleşme dalını uygulama dalına kontrollü birleştir.
4. Diagnostics ve active-config publisher'larını ortak `caba72c` tam
   vektörleriyle tamamla.
5. Output write-violation detection ekle.
6. VM'den dört output bloğunu tek kalıcı oturumda yeniden FC03 test et.
7. Aktüatör enerjisizken controlled-stop FC16 + accepted sequence testi yap.
8. AUTO steering entegrasyonunu bundan sonra ele al.

# PLC–ROS–ESP Uyumluluk Kararları

Bu belge S7-1200 PLC uygulamasının `rover_core_ros2` ve
`rover-g16-gateway-firmware` ile aynı güvenlik ve wire sözleşmesini
uygulaması için gerekli kararları sabitler. TIA/SCL kodu içermez; PLC
geliştiricisinin uyması gereken mimari sınırı ve kabul kriterlerini tanımlar.

Karar statüleri:

- **FIXED:** protokol v1.1'in değişmez parçası;
- **PLC:** TIA uygulamasında izlenecek davranış;
- **SAFETY-EXTERNAL:** standart PLC/Modbus yazılımından bağımsız fiziksel kat;
- **DEPLOYMENT:** araç kontrol ağı kurulurken atanacak değer;
- **HIL-GATE:** ölçüm/test kanıtı olmadan üretim değeri seçilemez;
- **TIA-EVIDENCE:** gerçek cihaz/proje görülünce kaydedilecek bilgi;
- **UPSTREAM-ACTION:** ana ROS sözleşmesinde kapatılması zorunlu tanım.

## 1. Kaynak otoritesi ve sürüm

**FIXED**

Ana protokol otoritesi `rover_core_ros2` deposudur:

- referans commit:
  `caba72c7cce4fdc64328caa1b586c3be68077b23`;
- kaynak dal:
  `rover-core-ros2/agent/local-metric-map`;
- makine-okunur şema:
  `rover_hardware/config/plc_protocol_v1.yaml`;
- ortak test vektörleri:
  `rover_hardware/config/plc_protocol_v1_test_vectors.yaml`;
- insan-okunur sözleşme:
  `docs/PLC_ORIN_G16_HABERLESME_SOZLESMESI.md`;
- ESP profili:
  `rover_hardware/config/g16_gateway.yaml`.

Protokol wire sürümü:

| Alan | Değer |
|---|---:|
| major | `1` |
| minor | `1` |
| block length | 64 register |
| Modbus Unit ID | `1` |
| register byte order | big-endian |
| multi-register word order | high-word-first |
| float | IEEE-754 binary32 |
| CRC | CRC-32/ISO-HDLC |

Makine-okunur YAML sürüm ve offset otoritesidir. İnsan-okunur sözleşme de
`caba72c` ile `protocol_minor = 1` olarak düzeltilmiştir. PLC wire üzerinde
yalnız tam `1.1` eşleşmesini kabul eder ve `1.1` yayınlar.

ESP tarafının ayrıntılı davranış otoritesi:
[rover-g16-gateway-firmware/DECISIONS.md](https://github.com/kzlslngl/rover-g16-gateway-firmware/blob/agent/phase1-foundation/DECISIONS.md)

Bu depoda offset, enum, bit veya alan anlamı bağımsız değiştirilmez.

## 2. PLC'nin sistem rolü

**FIXED**

- PLC nihai hareket otoritesidir.
- Orin yalnız fiziksel anlamı açık hız, direksiyon, ivme/yavaşlama ve
  controlled-stop hedefleri gönderir.
- Orin gaz, fren, motor pulse, safety reset veya STO bypass göndermez.
- Orin `MANUAL` talep edemez.
- G16 manuel veri yolu Orin kapalıyken çalışabilir.
- PLC komut kaynağını safety, MANUAL ve AUTO guard'larından sonra seçer.
- Web UI veya tablet PLC register'larına doğrudan erişmez.
- Ham Modbus buffer hiçbir koşulda doğrudan kontrol hesabına girmez.
- Limit dışı değer clamp edilmez; snapshot açık bir nedenle reddedilir.

## 3. Safety sınırı

**SAFETY-EXTERNAL**

Modbus TCP ve standart S7-1200 kontrol programı safety-rated kabul edilmez.
Aşağıdaki zincir haberleşmeden bağımsızdır:

- fiziksel E-stop;
- safety relay veya uygun F-CPU;
- drive STO;
- kontaktör enerjisi ve geri beslemesi;
- mekanik/fiziksel fren safe-state.

E-stop aktif olduğunda kontrollü rampa güvenlik fonksiyonu olarak beklenmez:
drive inhibit/STO fiziksel zincirden uygulanır. PLC state yalnız durumu
`ESTOP_ACTIVE` olarak raporlar.

E-stop reset, safety bypass, STO bypass ve safety force Modbus protokolünde
bulunmaz.

## 4. Haberleşme topolojisi

**FIXED**

```text
Orin/ROS 2 -- Modbus TCP client --> S7-1200 MB_SERVER
S7-1200 MB_CLIENT -- FC03 -------> ESP32-ETH01 MB_SERVER
```

Orin bağlantısı:

- Orin tek yetkili command writer'dır;
- command block yazımı protokol gereği tek FC16 isteğidir;
- state/G16/diagnostics/config okuması FC03'tür;
- PLC server TCP portu 502'dir.

ESP bağlantısı:

- PLC ayrı bir `MB_CLIENT` instance'ı kullanır;
- yalnız FC03 ile ESP absolute offset 320-383 okunur;
- sonuç yerel 64-WORD raw receive buffer'a yazılır;
- ESP bağlantısı Orin bağlantısından bağımsızdır.

**DEPLOYMENT**

- PLC, Orin ve ESP statik IP/subnet/VLAN planı ortak deployment config'te
  tutulur;
- TCP 502 yalnız kontrol VLAN'ında açılır;
- switch/firewall ACL, PLC server'a yalnız Orin IP'sini kabul eder;
- bakım laptopu üretim hareket durumunda command writer olamaz.

Standart `MB_SERVER` pasif bağlantıda istemci kimliğini safety
authentication olarak doğrulamaz. IP/VLAN kısıtı safety kanıtı değil,
zorunlu defense-in-depth katmanıdır.

## 5. Siemens MB_SERVER kısıtı

**FIXED + PLC**

Siemens'in resmî S7-1200 dokümanına göre:

- `MB_HOLD_REG` non-optimized global DB veya M memory olmalıdır;
- aynı holding alanı FC03, FC06, FC16 ve FC23 erişimine açıktır;
- Modbus TCP instruction için CPU firmware en az V4.1 olmalıdır.

Kaynak:
[Siemens S7-1200 System Manual update – MB_SERVER](https://support.industry.siemens.com/cs/attachments/109743003/s71200_manual_update_en-US_en-US.pdf)

Bunun sonucu:

- `read_only` wire tanımı standart `MB_SERVER` tarafından adres bazında
  otomatik uygulanmaz;
- PLC state/G16/diagnostics/config bloklarına gelen dış yazmalar kontrol
  mantığını değiştiremez;
- PLC output blokları her scan sonunda PLC'nin typed otoritesinden yeniden
  encode edilir;
- output bölgesindeki beklenmeyen değişim contract violation olarak sayılır;
- ihlal AUTO sırasında görülürse Orin command link invalid olur ve
  `CONTROLLED_STOP` başlatılır;
- safety ve aktüatör hesabı raw output register'lardan veri okumaz.

Standart `MB_SERVER` kullanılan prototipte function-code bazlı gerçek
write-filter sağlandığı varsayılmaz. Orin'in FC16 kullanma zorunluluğu,
snapshot bütünlüğü ve ağda tek writer birlikte uygulanır. Üretimde adres ve
function-code seviyesinde zorunlu filtre istenirse standart `MB_SERVER`
yerine bu yeteneği kanıtlanmış server/gateway gerekir; protokol varsayımla
güvenli ilan edilmez.

## 6. DB yerleşim kararı

**PLC**

Fiziksel DB numarası wire protokolün parçası değildir. Tüm program sembolik
DB adları kullanır; numaralar TIA projesinde çakışmasız atanır ve deployment
kaydına yazılır.

### Raw communication DB'leri

| Sembolik ad | İçerik | Özellik |
|---|---|---|
| `DB_ModbusServerRaw` | `ARRAY[0..319] OF WORD` | global, non-optimized, non-retentive |
| `DB_EspGatewayRxRaw` | `ARRAY[0..63] OF WORD` | communication buffer, non-retentive |
| `DB_ExpectedPublishedRaw` | PLC output bloklarının beklenen kopyası | control kaynağı değildir |
| `DB_MbServerInstance` | MB_SERVER instance | sembolik erişim |
| `DB_EspMbClientInstance` | MB_CLIENT instance | sembolik erişim |
| `DB_OrinConnection` | `TCON_IP_v4` ve bağlantı config'i | deployment-owned |
| `DB_EspConnection` | MB_CLIENT bağlantı config'i | deployment-owned |

`DB_ModbusServerRaw[0..63]` command ingress alanıdır.
`DB_ModbusServerRaw[64..319]` PLC tarafından yayımlanan dört output bloktur.
Raw DB boot'ta sıfırlanır ve retentive değildir.

### Typed çalışma DB'leri

| Sembolik ad | Görev |
|---|---|
| `DB_ValidatedOrinCommand` | son kabul edilmiş typed command |
| `DB_ValidatedG16Input` | ESP snapshot doğrulama sonucu |
| `DB_G16Calibration` | sürümlü mapping/endpoint/deadband/neutral |
| `DB_ControlState` | state machine ve authority |
| `DB_PlcStatePublisher` | typed PLC state staging |
| `DB_Diagnostics` | yerel diagnostic sayaçları |
| `DB_ActiveConfig` | gerçekten uygulanan internal config |
| `DB_SafetyInputs` | safety/interlock giriş aynası |
| `DB_ActuatorState` | hedef, feedback ve validity |

Typed DB'ler optimized olabilir. Retentivity alan bazında açıkça seçilir;
hareket hedefi, raw command, geçerlilik cache'i ve aktüatör komutu retentive
olamaz.

Retentive kalmasına izin verilen bilgiler:

- PLC boot/session counter;
- config version/CRC;
- diagnostic lifetime counter'ları.

Boot sonrası önceki hareket komutu veya authority geri yüklenmez.

## 7. Wire register blokları

**FIXED**

| Offset | Boyut | Blok | Wire sahibi |
|---|---:|---|---|
| `0-63` | 64 | `ORIN_TO_PLC_COMMAND` | Orin |
| `64-127` | 64 | `PLC_TO_ORIN_STATE` | PLC |
| `128-191` | 64 | `G16_STATUS` | PLC |
| `192-255` | 64 | `PLC_DIAGNOSTICS` | PLC |
| `256-319` | 64 | `ACTIVE_CONFIG` | PLC |
| ESP server `320-383` | 64 | `ESP_TO_PLC_G16_INPUT` | ESP |

Her 64-register blok:

```text
magic + protocol major/minor + length
begin_sequence
payload + reserved zeros
crc32
end_sequence
```

CRC-32/ISO-HDLC ilk 60 register'ın high-byte/low-byte akışı üzerinden
hesaplanır. CRC ve end sequence kapsam dışıdır.

PLC output snapshot'ı typed staging alanında tamamen oluşturulur, reserved
alanları sıfırlanır, CRC hesaplanır ve aynı begin/end sequence ile raw
server alanına tek scan içinde kopyalanır.

## 8. Command ingress ve kabul sırası

**PLC**

PLC `DB_ModbusServerRaw[0..63]` alanını MB_SERVER çağrısından sonra ayrı bir
staging kopyasına alır. Validation sırasında raw DB tekrar okunmaz.

İlk başarısız kontrol reject reason olur:

1. magic, block length, begin/end eşitliği ve reserved-zero;
2. protocol major/minor;
3. CRC;
4. Orin session;
5. heartbeat ilerlemesi ve heartbeat age;
6. command sequence ilerlemesi ve command age;
7. `command_validity_ms` ve PLC üst limiti;
8. bütün float alanların finite olması;
9. fiziksel range ve pozitif limit kontrolleri;
10. E-stop/safety;
11. kritik fault;
12. interlock;
13. manual override;
14. autonomy permission;
15. localization/navigation/geofence/mission-time guard'ları.

Reject eşlemesi ana enum değerlerini kullanır:

- bozuk header/begin-end/reserved: `INVALID_SNAPSHOT`;
- sürüm: `PROTOCOL_MISMATCH`;
- CRC: `CRC_ERROR`;
- yeni Orin session: `SESSION_CHANGED_REARM_REQUIRED`;
- heartbeat: `HEARTBEAT_STALE`;
- command validity/age: `COMMAND_STALE`;
- duplicate/out-of-order sequence: `SEQUENCE_NOT_ADVANCING`;
- NaN/Inf: `VALUE_NOT_FINITE`;
- range: `VALUE_OUT_OF_RANGE`.

Duplicate snapshot gelmesi önceki kabul edilmiş komutu hemen silmez.
Önceki komut yalnız kendi validity ve PLC timeout penceresi boyunca tutulur;
pencere dolunca AUTO için controlled stop başlar.

Orin ve PLC monotonic saatleri ayrı clock domain'leridir.
`orin_monotonic_ms` değeri PLC monotonic zamanından doğrudan çıkarılmaz.
PLC:

- heartbeat age'i heartbeat değerinin son ilerlediğini gördüğü yerel PLC
  zamanından;
- command age'i command sequence değerinin son ilerlediğini gördüğü yerel PLC
  zamanından

hesaplar. `command_validity_ms` bu yerel kabul zamanına uygulanır.
`orin_monotonic_ms` yalnız Orin saatinin kendi içinde ilerlediğini, wrap veya
geri sıçrama anomalisini denetlemek için kullanılır.

Yeni Orin session:

- eski accepted command cache'ini invalid eder;
- AUTO re-arm gerektirir;
- araç aktif AUTO ise controlled stop başlatır;
- yeni session'dan ilk snapshot doğrudan hareket başlatamaz.

`CONTROLLED_STOP_REQUEST`, aynı snapshot'taki hareket hedeflerinden daha
yüksek önceliklidir.

## 9. Authority ve state-machine önceliği

**FIXED + PLC**

Otorite önceliği:

```text
ESTOP
  > FAULT_LOCKOUT
  > CONTROLLED_STOP
  > MANUAL
  > AUTONOMOUS_ACTIVE
  > AUTONOMOUS_READY
  > SAFE_DISABLED
```

State kuralları:

- Boot `POWER_UP` ve drive inhibit ile başlar.
- Safety/config geçerli olmadan `SAFE_DISABLED` dışına çıkılmaz.
- E-stop her state'ten `ESTOP_ACTIVE` durumuna geçer.
- Kritik fault her hareket state'inden `FAULT_LOCKOUT` durumuna geçer.
- AUTO command/session/heartbeat/localization/navigation/geofence kaybı
  `CONTROLLED_STOP` başlatır.
- AUTO sırasında MANUAL talebi önce controlled stop, sonra
  `MANUAL_ARMING` neutral handshake uygular.
- G16 kaybı MANUAL sırasında controlled stop başlatır.
- Orin kaybı geçerli MANUAL yolunu tek başına kesmez.
- Controlled stop tamamlanınca authority `SAFE_DISABLED` olur; yeniden
  hareket için yeni arming gerekir.
- Ağ reconnect tek başına AUTO veya MANUAL başlatmaz.
- E-stop reset ağdan yapılamaz.

`active_authority` eşlemesi:

- `POWER_UP`, `SAFE_DISABLED`, `MANUAL_ARMING`, `AUTO_ARMING`:
  `SAFE_DISABLED`;
- `MANUAL`: `MANUAL`;
- `AUTONOMOUS_READY`: `AUTONOMOUS_READY`;
- `AUTONOMOUS_ACTIVE`: `AUTONOMOUS_ACTIVE`;
- `CONTROLLED_STOP`: `CONTROLLED_STOP`;
- `FAULT_LOCKOUT` ve `ESTOP_ACTIVE`: `FAULT_LOCKOUT`.

## 10. G16 / ESP kabul kararı

**FIXED + PLC**

PLC ESP bloğunu yalnız aşağıdakilerin tamamında kabul eder:

- magic/version/length doğru;
- begin/end eşit;
- CRC doğru;
- session bilinen;
- gateway heartbeat ilerliyor;
- SBUS frame counter ilerliyor;
- frame age PLC aktif limitinde;
- `FRAME_VALID = 1`;
- lost, failsafe ve decoder fault kapalı;
- `channel_count = 16`;
- gerekli kanal mask bitleri geçerli.

Gateway heartbeat ve SBUS frame counter'ın her PLC poll'unda değişmesi
gerekmez. PLC her sayaç için son ilerlemeyi gördüğü yerel monotonic zamanı
tutar; sayaç ilgili configured freshness penceresinde en az bir kez
ilerlemiyorsa bağlantı stale olur. Duplicate FC03 sonucu tek başına anlık
fault değildir.

`gateway_monotonic_ms` ile PLC monotonic zamanı doğrudan çıkarılmaz.
PLC'nin yerel counter-age ölçümü ile gateway'in yayınladığı `frame_age_ms`
birlikte geçerli olmalıdır. İkisinden biri limit dışındaysa G16 invalid olur.

ESP session değişimi:

- son G16 snapshot'ını invalid eder;
- MANUAL neutral/re-arm handshake gerektirir;
- eski kanal değerini hareket komutu olarak kullanmaz.

PLC manuel kontrol kaynağı `DB_ValidatedG16Input` ve sürümlü calibration
DB'sidir. Orin'e sunulan `G16_STATUS` raw Modbus aynası kontrol kaynağı
değildir.

Kalibrasyon geçerli değilse:

- `CHANNEL_CALIBRATION_VALID = 0`;
- normalized kanallar sıfır yayınlanır;
- `MANUAL_SIGNAL_VALID = 0`;
- MANUAL authority yasaktır.

ESP v1.1 link-quality/RSSI sağlamadığından ilgili valid bitleri sıfır ve
değerleri sıfırdır.

## 11. Tamamlanan upstream wire alanları

**FIXED**

Ana ROS commit `caba72c` ile aşağıdaki önceki upstream açıkları kapanmıştır:

- `g16_summary_flags` bit eşlemesi;
- `fault_bits` bit eşlemesi;
- `interlock_bits` bit eşlemesi;
- `PLC_DIAGNOSTICS` register `192..255` payload'ı;
- `ACTIVE_CONFIG` register `256..319` payload'ı;
- PLC state, G16 status, diagnostics, active config ve ESP snapshot için tam
  64-register bilinen-sonuç vektörleri;
- reserved register'ların sıfır ve protocol minor'ın tam eşit olma kuralı.

Kesin bit, enum, offset, validity ve test CRC değerleri
[`MAIN_PROTOCOL_HANDOFF_CABA72C.md`](MAIN_PROTOCOL_HANDOFF_CABA72C.md)
belgesindedir. PLC eski geçici “payload reserved/sıfır” davranışını yeni
uygulamada sürdürmez; typed publisher'ları kesin wire alanlarına encode eder.

Geçerlilik davranışı:

- `g16_summary_flags`, `fault_bits` ve `interlock_bits` yalnız tanımlı bitleri
  kullanır; diğer bitler sıfırdır;
- diagnostics/config bloklarının yalnız tanımlı payload alanları encode
  edilir; belgelenmiş reserved register'lar sıfırdır;
- `ACTIVE_CONFIG_VALID`, doğrulanmış config ve zorunlu config-validity
  bitleri birlikte sağlanmadan açılmaz;
- `BRAKE_EFFECT_VALID`, `FEEDBACK_UNITS_VALID` olmadan açılmaz.

Internal `DB_ActiveConfig` geçerliliği ile wire
`status_flags.ACTIVE_CONFIG_VALID` aynı şey değildir. Alanların tanımlanmış
olması config değerlerini otomatik olarak production-valid yapmaz; gerçek
timeout ve hareket limitleri HIL kapısına tabidir.

## 12. Timeout, limit ve config politikası

**PLC + HIL-GATE**

Timeout ve hareket limitleri kod içine dağınık literal olarak yazılmaz;
`DB_ActiveConfig` typed internal alanlarından okunur.

Config en az şunları içerir:

- Orin heartbeat timeout;
- command timeout ve izin verilen `command_validity_ms` üst limiti;
- ESP response timeout;
- G16 frame stale timeout;
- controlled-stop limitleri;
- araç hızı, direksiyon, ivme/yavaşlama ve steering-rate limitleri;
- G16 calibration version/CRC;
- `stop_on_g16_loss = true`;
- config version/CRC ve configured flags.

Gerçek sayısal değerler araç geometrisi, fren ve HIL testi olmadan
production-final değildir.

Bu değerler doğrulanana kadar:

- internal config valid kapalıdır;
- `AUTONOMOUS_PERMITTED = 0`;
- MANUAL ve AUTO hareket yasaktır;
- fiziksel çıkışlar inhibit kalır;
- yalnız communications/validation/watch-table testi yapılır.

Sıfır değer “TBD” anlamında kullanılmaz; her gerekli config alanının ayrı
configured/valid biti vardır.

## 13. PLC session ve restart

**PLC**

- Her CPU startup'ta sıfır olmayan yeni `plc_session_id` üretilir.
- Session, retentive boot counter ve CPU/device kimliğinin tanımlı
  birleşiminden üretilir.
- Retentive boot counter startup başına bir kez ilerler.
- Session üretilemezse hareket izinleri kapalı kalır.
- Raw command, accepted command, authority ve actuator target retentive
  değildir.
- PLC restart sonrası Orin state cache'ini invalid eder.
- Restart sonrası AUTO/MANUAL otomatik geri yüklenmez.

PLC output:

- `plc_heartbeat_counter` her yeni state snapshot'ında artar;
- output begin/end sequence her yeni snapshot'ta aynı yeni değere ilerler;
- monotonic zaman wrap-around ile çalışır;
- sayaç wrap reset sayılmaz, session değişimi reset kanıtıdır.

## 14. PLC scan sırası

**PLC**

1. Fiziksel safety, interlock ve feedback girişlerini örnekle.
2. MB_SERVER ve ESP MB_CLIENT communication bloklarını çalıştır.
3. Raw output bölgesinde beklenmeyen dış yazma olup olmadığını karşılaştır.
4. Orin command ve ESP raw snapshot'larını ayrı staging alanlarına kopyala.
5. Header/CRC/session/freshness/range kontrollerini çalıştır.
6. Yalnız geçerli sonuçları typed çalışma DB'lerine atomik kabul et.
7. Timeout, restart ve config-valid guard'larını hesapla.
8. Authority state machine'i çalıştır.
9. Controlled stop veya normal trajectory/rate limitlerini uygula.
10. Safety/interlock guard'larından sonra actuator target üret.
11. Feedback, state ve yerel diagnostics typed snapshot'larını oluştur.
12. PLC output bloklarını encode et, CRC/sequence ekle ve raw server alanına
    kopyala.

Communication bloğunun success biti hareket izni değildir.

## 15. TIA ve cihaz kanıtı

**TIA-EVIDENCE**

İlk gerçek PLC download işleminden önce depoya kaydedilir:

- TIA Portal tam sürümü ve update seviyesi;
- CPU tam MLFB/order code;
- CPU firmware sürümü;
- MB_SERVER ve MB_CLIENT instruction/library sürümü;
- Profinet interface ve port bilgisi;
- fiziksel DB numarası -> sembolik DB adı tablosu;
- DB optimized/non-optimized ve retentive özellikleri;
- connection ID'leri ve statik IP planı;
- PLC compile sonucu ve uyarılar;
- PLCSIM/gerçek CPU test ayrımı;
- proje archive SHA veya release etiketi.

CPU firmware en az Siemens Modbus instruction gereksinimini karşılamalıdır;
yalnız “S7-1200” model adı yeterli kanıt değildir.

Bu VM'de TIA Portal, PLC compile veya cihaza download çalıştırılmaz.

## 16. Zorunlu kabul testleri

1. CRC check ve endian scalar test vektörleri.
2. Ana command snapshot known-result testi.
3. Bad magic/version/length/begin-end/reserved/CRC.
4. Duplicate, out-of-order ve modulo-`2^32` sequence wrap.
5. Orin, PLC ve ESP session değişimi.
6. Heartbeat ilerlerken command sequence freeze ve tersi.
7. NaN, Inf ve bütün range sınırları.
8. FC16 command yazımı ve torn snapshot enjeksiyonu.
9. FC06/FC23 ile parçalı command oluşturma denemesi.
10. PLC output bölgesine dış yazma ve aynı scan'de yeniden yayınlama.
11. Yetkisiz client IP ve reconnect.
12. G16 freeze/lost/failsafe/bad CRC/session reset.
13. AUTO command loss -> controlled stop.
14. AUTO -> MANUAL controlled stop + neutral handshake.
15. MANUAL sırasında Orin kaybının manuel yolu kesmemesi.
16. MANUAL G16 kaybı -> controlled stop.
17. E-stop aktifken ağ komutunun çıkış üretememesi.
18. Config invalid iken drive enable oluşmaması.
19. PLC restart sonrası authority'nin geri yüklenmemesi.
20. Mock PLC ve gerçek PLC wire snapshot eşdeğerliği.

Ana ROS test vektörleri artık command, PLC state, G16, diagnostics, active
config ve ESP bloklarının tamamı için known-result değerleri içerir. PLC test
FB/watch table çıktısı ana YAML'daki 64 register ile birebir karşılaştırılır;
yalnız CRC değerinin tutması yeterli kabul edilmez.

## 17. PLC değişiklik kontrol listesi

Her PLC PR/değişikliğinde:

- [ ] ana protokol commit'i ve v1.1 kaydedildi;
- [ ] raw DB kontrol kaynağı olarak kullanılmadı;
- [ ] raw communication DB'leri non-retentive;
- [ ] MB_SERVER raw alanı non-optimized;
- [ ] reserved wire alanlarına yeni anlam uydurulmadı;
- [ ] bütün snapshot'larda CRC ve eşit sequence var;
- [ ] reject reason deterministik validation sırasından geliyor;
- [ ] E-stop/STO/relay yazılım haberleşmesinden bağımsız;
- [ ] config invalid iken hareket izinleri kapalı;
- [ ] PC/TIA compile ve test kanıtı ayrı raporlandı;
- [ ] donanım gerektiren test çalışmadıysa açıkça belirtildi;
- [ ] wire değişikliği önce ana ROS sözleşmesine işlendi.

## 18. Proje kimliği, ihtiyaçların kaynağı ve denetim rolü

### Bu bileşenin kimliği

Bu depo rover'ın Siemens S7-1200 kontrol bileşenidir. Görevi Orin ve G16
kaynaklarını doğrulamak, nihai kontrol otoritesini seçmek, controlled-stop ve
interlock kurallarını uygulamak ve yalnız doğrulanmış hedefleri araç kontrol
katmanına aktarmaktır.

Bu bileşen:

- ROS 2 görev planlayıcısı değildir;
- ESP32 SBUS decoder firmware'i değildir;
- safety relay, E-stop veya drive STO yerine geçmez;
- ham Modbus register'larını doğrudan hareket komutu olarak kullanmaz.

### Kuralların sistem gerekçesi

PLC, Orin ve ESP ayrı depolarda ve ayrı geliştirme ortamlarında yazılır.
CRC, endian, offset, session, freshness, authority veya restart anlamlarından
yalnız birinin farklı uygulanması dahi aynı register değerinin farklı
yorumlanmasına ve güvenli olmayan hareket kararına yol açabilir. Bu belge,
ayrı geliştirilen PLC projesinin ana rover sistemiyle aynı sözleşmeyi
uygulaması için gereken ortak sınırdır.

### İsteklerin ve kararların kaynağı

Ana sistem ve sözleşme kaynağı:
[kzlslngl/rover-core-ros2](https://github.com/kzlslngl/rover-core-ros2)

Bu belgenin güncel referansı:
`caba72c7cce4fdc64328caa1b586c3be68077b23`

Talepler özellikle şu ana proje kaynaklarından gelir:

- `rover_hardware/config/plc_protocol_v1.yaml`;
- `rover_hardware/config/plc_protocol_v1_test_vectors.yaml`;
- `rover_hardware/config/g16_gateway.yaml`;
- `docs/PLC_ORIN_G16_HABERLESME_SOZLESMESI.md`;
- `docs/SISTEM_GEREKSINIMLERI_VE_KARARLAR.md`;
- `docs/ROS2_NAV2_CALISMA_PLANI.md`.

Bu PLC deposu uygulama deposudur; wire protokolün bağımsız otoritesi değildir.
Bu belge ile ana ROS şeması çelişirse geliştirici sessizce birini seçmez:
çelişki kaydedilir, ana sözleşme düzeltilir/sürümlenir ve ardından PLC
uygulaması güncellenir.

### Belgeyi hazırlayan Ana Proje Codex'i: denetim rolü

Ben bu belgeyi hazırlayan **Ana Proje Codex'i**yim. Çalışma kaynağım ve sistem
otoritem `rover-core-ros2` projesidir; buradaki görevim rover sistem uyumluluğu
ve güvenlik mimarisi denetimidir. Ben PLC geliştirme projesinde çalışan PLC
Codex'i değilim.

Bu rol:

- TIA/SCL uygulama kodunu yazmaz veya değiştirmez;
- PLC compile, PLCSIM veya cihaza download çalıştırmaz;
- mevcut kodu ve Git diff'lerini salt-okunur inceler;
- ana ROS sözleşmesine aykırı, belirsiz veya kanıtsız yapıları tespit eder;
- bulguları ve gerekli kabul kriterlerini yalnız Markdown belgeleriyle
  geliştiriciye aktarır;
- düzeltmenin nasıl uygulanacağına mimari yön verir, uygulamayı PLC geliştirme
  projesine bırakır.

Bu not bir otomatik onay değildir. PLC kodunun uygunluğu ancak ilgili commit,
TIA compile kanıtı, test vektörleri, PLCSIM/gerçek CPU testleri ve donanım
güvenlik kapıları yeniden incelendikten sonra kabul edilir.

### PLC Codex'i: uygulama rolü ve ilk görev

PC'de bu depo için açılacak **PLC Codex'i** uygulama sahibidir. Bu rol:

- TIA Portal projesini, SCL/UDT/DB kaynaklarını ve test bloklarını oluşturabilir
  ve değiştirebilir;
- PC'de TIA compile, PLCSIM ve kullanıcı onayıyla gerçek CPU testlerini
  çalıştırabilir;
- metin/SCL/XML dışa aktarımlarını ve test kanıtlarını bu depoda
  sürümleyebilir;
- `DECISIONS.md`, `PLC_INTEGRATION_GUIDE.md` ve
  `ORIN_PLC_DB_TAG_CONTRACT.md` belgelerini zorunlu giriş sözleşmesi olarak
  kullanır;
- offset, endian, CRC, bit, enum, session, freshness veya authority anlamını
  kendi başına değiştirmez; çelişkiyi Ana Proje Codex'ine ve ana sözleşmeye
  upstream bulgu olarak iletir;
- safety/HIL kapıları sağlanmadan gerçek aktüatör çıkışı veya hareket üretmez.

İlk uygulama hedefi fiziksel çıkışsızdır: TIA/CPU sürümünü kaydetmek, ham
transport DB'lerini ve typed UDT'leri oluşturmak, endian ile CRC yardımcılarını
bilinen-sonuç vektörüyle doğrulamak ve ESP snapshot validator sonucunu yalnız
watch/diagnostics alanında göstermek.

## 19. 20 Ağustos 2026 uygulama dalı uyumluluk incelemesi

**PLC**

GitHub'daki `motion-steering-control` uygulama dalı `main` üzerinden
geliştirilmiş; bu belgenin bulunduğu `agent/plc-contract-decisions` dalını
içermemektedir. PLC Codex'i yeni uygulamaya devam etmeden önce bu iki dalın
geçmişini kontrollü biçimde birleştirmeli ve en az şu belgeleri uygulama
dalında görünür tutmalıdır:

- `DECISIONS.md`;
- `PLC_INTEGRATION_GUIDE.md`;
- `ORIN_PLC_DB_TAG_CONTRACT.md`.

Bu bir kod birleştirme talimatı değil, sözleşme kapısıdır. Çakışmada uygulama
dalı sessizce üstün sayılmaz; ana ROS şeması otoritedir.

Mevcut `FB_G16SnapshotValidator` incelemesinde `sbus_frame_counter`
accepted typed DB'ye ve diagnostics'e aktarılmakta, fakat ilerleme yaşı
`DataValid` kararında kullanılmamaktadır. Bölüm 10 ve ana ROS sözleşmesi
gereği PLC:

- son farklı SBUS frame counter değerini;
- bu ilerlemeyi gördüğü yerel monotonic zamanı;
- configured frame-counter freshness penceresini

ayrı tutmalı ve pencere aşımını G16 invalid/reject nedeni yapmalıdır. Her FC03
poll'unda sayaç değişmesi gerekmez; duplicate gateway snapshot anlık fault
değildir.

20 Ağustos handoff değerlerinin statüsü:

| Değer | Statü |
|---|---|
| PLC `192.168.2.100/24`, ESP `192.168.2.166/24` | doğrulanmış bench |
| firmware gateway `192.168.2.241` | eski bench; production için geçersiz |
| `MaxFrameAgeMs=100 ms` | bench/HIL adayı |
| `PollTimeout=T#500ms` | bench/HIL adayı |
| üç farklı sağlıklı snapshot | re-arm başlangıç adayı |
| neutral hold `T#500ms` | bench/HIL adayı |
| AUTO G16 grace `T#2s` | versioned safety config olmadan production değil |

G16 kanal tablosunda doğrudan ölçülmeyen ortak analog aralıklar doğrulanmış
kalibrasyon gibi gösterilmez. Kanal mapping sürümü, min/nötr/max, deadband,
yön ve tolerans gerçek ölçüm kanıtıyla kaydedilmeden MANUAL production kapısı
açılmaz.

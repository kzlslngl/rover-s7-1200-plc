# PLC Restart/Replay Fiziksel Kabulü — 24 Ağustos 2026

Bu belge Ana Proje Codex'i tarafından, PLC Codex'inden gelen PLC boot-session
ve eski Orin command replay korumasının fiziksel kabul kanıtı olarak
hazırlanmıştır.

Ana proje codec/sözleşme otoritesi:

`rover-core-ros2/agent/local-metric-map@854fee6f67ad3cb37f526c84fbcf79cdcacf10fa`

## Güvenlik sınırı ve topoloji

| Alan | Değer |
|---|---|
| PLC | `192.168.2.100:502`, unit ID `1` |
| Command | FC16, offset `0`, quantity `64` |
| State | FC03, offset `64`, quantity `64` |
| Mod | Yalnız `CONTROLLED_STOP (3)` |
| Command flags | `0x0005`: `COMMAND_VALID + CONTROLLED_STOP_REQUEST` |
| Target speed / steering | `0.0 m/s / 0.0 rad` |
| AUTO / MANUAL talebi | Hiç gönderilmedi |
| PLC güvenlik durumu | `FAULT_LOCKOUT`, drive inhibit açık |
| PLC program işlemi | Download yapılmadı |
| Restart | Kullanıcı tarafından normal güç kesme/açma |

Komut ve state işlemleri her canlı fazda tek sahipli, kalıcı bir Modbus TCP
session üzerinden sıralı yürütüldü. Restart sırasında ve yeniden açılış
kontrolünde yalnız FC03 kullanıldı. Replay fazında kaydedilmiş snapshot yalnız
bir FC16 isteğiyle bir kez yazıldı; re-arm üretilmedi.

## Sonuç özeti

| Aşama | Beklenen | Fiziksel sonuç | Karar |
|---|---|---|---|
| İlk güvenli stream | Re-arm sonrası command kabulü | Reject `5 -> 0`, accepted `0x64082401 / 313` | Geçti |
| PLC restart | PLC session değişmeli, eski kabul silinmeli | Session `4 -> 5`, accepted `0 / 0`, link invalid | Geçti |
| Eski snapshot replay | Invalid + re-arm required + ilk reject `5` | Yaklaşık `105 ms` içinde reject `5`, invalid, re-arm required | Geçti |
| Replay güvenliği | AUTO/MANUAL ve hareket yolu oluşmamalı | Authority `FAULT_LOCKOUT`, drive disabled/inhibited, sıfır hedef | Geçti |
| Recovery | Taze sayaç + temiz re-arm ile kabul | Reject `5 -> 0`, accepted `0x64082401 / 595` | Geçti |
| Stream sonrası | Heartbeat stale ile link düşmeli | Reject `6`, link invalid, accepted kimlik yalnız teşhis için korundu | Geçti |

## 1. Restart öncesi CONTROLLED_STOP kabulü

Preflight sırasında:

| Alan | Değer |
|---|---:|
| PLC session | `4` |
| PLC state sequence / heartbeat | `110843 / 110843` |
| PLC monotonic ms | `2216860` |
| Operational state / authority | `8 / 5` — `FAULT_LOCKOUT` |
| Status flags | `0x0000` |
| Fault / interlock | `0x00000400 / 0x00000123` |
| Accepted Orin session / command | `0 / 0` |
| Safety summary | `0x0005` — E-stop + drive inhibit |
| Raw actual speed | `0.0` |

Yeni Orin session `0x64082401` (`1678255105`) ile ilerleyen
`CONTROLLED_STOP` stream başlatıldı. İlk snapshot'ta PLC:

- `RejectReason=5 (SESSION_CHANGED_REARM_REQUIRED)`;
- `SessionRearmRequired=TRUE` (`interlock=0x00008123`);
- command link invalid;
- accepted session/command `0/0`

üretti. Kullanıcı TIA üzerinden, session görüldükten sonra temiz
`FALSE -> TRUE -> FALSE` `SessionRearm` kenarı uyguladı. Kabul edilen son
snapshot sequence, heartbeat ve command sequence `313 / 313 / 313` oldu.

Kabul anındaki PLC state:

| Alan | Değer |
|---|---:|
| PLC state sequence / heartbeat | `111781 / 111781` |
| PLC session | `4` |
| PLC monotonic ms | `2235620` |
| Status flags | `0x0200` — yalnız Orin command link valid |
| Reject reason | `0` |
| Accepted Orin session / command | `1678255105 / 313` |
| Operational state / authority | `8 / 5` — `FAULT_LOCKOUT` |
| Interlock / safety summary | `0x00000123 / 0x0005` |
| Raw actual speed | `0.0` |

Akış, kabul edilen snapshot kaydedildikten sonra kapatıldı ve TCP bağlantısı
sonlandırıldı.

## 2. Replay için kaydedilen tam ORIN_COMMAND snapshot

Ana ROS codec'i aşağıdaki 64 register'ı tekrar decode ederek doğruladı:

| Alan | Değer |
|---|---:|
| Magic / protocol / length | `0x5243 / 1.1 / 64` |
| Begin / end sequence | `313 / 313` |
| Orin session | `0x64082401` (`1678255105`) |
| Heartbeat / command sequence | `313 / 313` |
| Orin monotonic ms | `1131379` |
| Requested mode / flags | `3 / 0x0005` |
| Target speed / steering | `0.0 / 0.0` |
| Accel / decel / steering-rate limit | `0.5 / 1.25 / 0.4` |
| Mission speed limit / validity | `2.0 / 250 ms` |
| Wire CRC | `0x30B39547` |

```text
00..07: 5243 0001 0001 0040 0000 0139 6408 2401
08..15: 0000 0139 0000 0139 0011 4373 0003 0005
16..23: 0000 0000 0000 0000 3F00 0000 3FA0 0000
24..31: 3ECC CCCD 4000 0000 0000 00FA 0000 0000
32..39: 0000 0000 0000 0000 0000 0000 0000 0000
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 30B3 9547 0000 0139
```

Reserved local `30..59` sıfırdır. CRC, register `0..59` üzerinden
CRC-32/ISO-HDLC ile yeniden hesaplanıp doğrulandı.

## 3. Normal güç restartı ve yeni PLC session

Komut akışı tamamen kapatıldıktan sonra kullanıcı PLC gücünü kesti ve tekrar
verdi. TIA download yapılmadı. Yeniden açılış sonrası üç ardışık salt-okunur
FC03 örneği:

| Örnek | PLC seq / heartbeat | Monotonic ms | PLC session | Accepted | Status / reject |
|---:|---|---:|---:|---|---|
| 1 | `622 / 622` | `12440` | `5` | `0 / 0` | `0x0000 / 0` |
| 2 | `632 / 632` | `12640` | `5` | `0 / 0` | `0x0000 / 0` |
| 3 | `644 / 644` | `12880` | `5` | `0 / 0` | `0x0000 / 0` |

Üç örnekte de:

- magic/type `0x5253`, protokol `1.1`, length `64`;
- begin=end, doğru CRC ve sıfır reserved local `48..59`;
- `FAULT_LOCKOUT`, authority `5`, drive inhibit açık;
- command link invalid ve accepted session/command `0/0`;
- raw actual speed `0.0`

doğrulandı. Böylece retentive boot counter'ın PLC session'ı `4 -> 5`
değiştirdiği ve validator kabul durumunun non-retentive sıfırlandığı fiziksel
olarak görüldü.

## 4. Eski snapshot'ın tek seferlik replay'i

Replay öncesi FC03 state sequence `3189`, PLC session `5`, accepted `0/0`,
link invalid, `FAULT_LOCKOUT`, drive inhibit açık ve raw actual speed `0.0`
idi. Kaydedilen 64 register, değiştirilmeden tek FC16 ile bir kez yazıldı.
Başka FC16 replay yapılmadı ve `SessionRearm` kenarı üretilmedi.

Kritik state gözlemleri:

| FC16 sonrası | PLC seq | Reject | Link valid | Rearm req. | Accepted | Cmd/HB age ms | Authority / speed |
|---:|---:|---:|---|---|---|---|---|
| `68.605 ms` | `3190` | `0` | Hayır | Hayır | `0 / 0` | `0 / 0` | `5 / 0.0` |
| `105.003 ms` | `3191` | `5` | Hayır | Evet | `0 / 0` | `12 / 12` | `5 / 0.0` |
| `132.601 ms` | `3192` | `5` | Hayır | Evet | `0 / 0` | `51 / 51` | `5 / 0.0` |
| `345.326 ms` | `3199` | `5` | Hayır | Evet | `0 / 0` | `250 / 274` | `5 / 0.0` |
| `517.829 ms` | `3204` | `5` | Hayır | Evet | `0 / 0` | `250 / 453` | `5 / 0.0` |
| `760.653 ms` | `3211` | `5` | Hayır | Evet | `0 / 0` | `250 / 500` | `5 / 0.0` |
| `999.603 ms` | `3219` | `5` | Hayır | Evet | `0 / 0` | `250 / 500` | `5 / 0.0` |

İlk FC03, PLC publisher'ın replay'i işlemesinden önceki bir state çevrimini
yakalamıştır. Bir sonraki örnekte beklenen ilk anlamlı sonuç oluşmuştur:

- `DataValid=FALSE` (`ORIN_COMMAND_LINK_VALID=0`);
- `SessionRearmRequired=TRUE` (`interlock=0x00008123`);
- `RejectReason=5 (SESSION_CHANGED_REARM_REQUIRED)`;
- accepted session/command `0/0`.

Heartbeat age `500 ms`'de doymasına rağmen validator reject `5` önceliğini
korudu; replay fazında reject `6`'ya geçmedi. İstek, timeout oluşursa reject
`6` kaydını opsiyonel kabul ettiğinden bu sonuç başarısızlık değildir. Recovery
akışı kapatıldıktan sonra normal heartbeat-stale reject `6` ayrıca görüldü.

## 5. Taze sayaçlarla recovery

Aynı Orin session `0x64082401` altında eski `313` snapshot bırakıldı ve
sequence/heartbeat/command sayaçları `314`'ten itibaren birlikte ileri
götürüldü. Bütün snapshot'lar yine `CONTROLLED_STOP`, flags `0x0005`, sıfır
hız ve sıfır steering içerdi.

Recovery preflight:

| Alan | Değer |
|---|---:|
| PLC seq / heartbeat | `5967 / 5967` |
| PLC session / monotonic | `5 / 119340 ms` |
| Reject / status | `5 / 0x0000` |
| Interlock | `0x00008123` — re-arm required |
| Accepted | `0 / 0` |
| Command / heartbeat age | `250 / 500 ms` |
| Authority / raw actual speed | `5 / 0.0` |

Kullanıcı TIA üzerinden temiz `FALSE -> TRUE -> FALSE` re-arm kenarı
uyguladı. Kabul edilen recovery snapshot:

| Alan | Değer |
|---|---:|
| Snapshot / heartbeat / command | `595 / 595 / 595` |
| Orin session | `0x64082401` |
| PLC seq / heartbeat | `6781 / 6781` |
| PLC session / monotonic | `5 / 135620 ms` |
| Status / reject | `0x0200 / 0` |
| Accepted session / command | `1678255105 / 595` |
| Interlock | `0x00000123` — re-arm biti temiz |
| Authority / raw actual speed | `5 / 0.0` |

```text
00..07: 5243 0001 0001 0040 0000 0253 6408 2401
08..15: 0000 0253 0000 0253 0015 BF10 0003 0005
16..23: 0000 0000 0000 0000 3F00 0000 3FA0 0000
24..31: 3ECC CCCD 4000 0000 0000 00FA 0000 0000
32..39: 0000 0000 0000 0000 0000 0000 0000 0000
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 B3EC 439C 0000 0253
```

Recovery stream, kabul kaydedildikten sonra kapatıldı.

## 6. Recovery sonrası fail-safe durum

Stream kapatıldıktan sonraki üç salt-okunur FC03 örneği:

| PLC seq / heartbeat | PLC session | Reject / status | Accepted | Cmd/HB age | Authority / speed |
|---|---:|---|---|---|---|
| `7827 / 7827` | `5` | `6 / 0x0000` | `1678255105 / 595` | `250 / 500` | `5 / 0.0` |
| `7837 / 7837` | `5` | `6 / 0x0000` | `1678255105 / 595` | `250 / 500` | `5 / 0.0` |
| `7848 / 7848` | `5` | `6 / 0x0000` | `1678255105 / 595` | `250 / 500` | `5 / 0.0` |

Accepted kimlik teşhis amacıyla korunurken link-valid düştü ve
`RejectReason=6 (HEARTBEAT_STALE)` oluştu. Yetki `FAULT_LOCKOUT`, drive inhibit
açık ve drive-enabled kapalı kaldı.

## Hareketsizlik kanıtının sınırı

Test boyunca gönderilen target speed ve steering her snapshot'ta tam
`0.0 / 0.0` idi; AUTO/MANUAL istenmedi. PLC hiçbir anda AUTO veya MANUAL
authority üretmedi, `DRIVE_ENABLED` biti açılmadı ve
`DRIVE_INHIBIT_ACTIVE` kapatılmadı. Raw actual speed her okumada `0.0` idi.

Ancak `ACTUAL_SPEED_VALID` status biti mekanik feedback henüz tamamlanmadığı
için kapalıdır. Bu nedenle raw `0.0`, tek başına geçerli hareket ölçümü
değildir. Fiziksel hareketsizlik kabulü; sıfır hareket komutu, PLC
`FAULT_LOCKOUT`, drive-disabled/inhibit interlock'ları ve operatörün
hareketsiz bench koşulu birlikte değerlendirilerek yapılmıştır.

## Nihai kabul

Fiziksel test aşağıdaki güvenlik özelliklerini doğruladı:

- normal power restart, retentive PLC session'ı `4 -> 5` değiştirdi;
- restart sonrası eski accepted command state korunmadı;
- eski ve daha önce kabul edilmiş tam snapshot, re-arm olmadan geçerli olmadı;
- ilk anlamlı replay sonucu reject `5` ve re-arm required oldu;
- replay sırasında accepted session/command `0/0` ve link invalid kaldı;
- AUTO/MANUAL authority veya drive-enable oluşmadı;
- taze sayaçlar ve bilinçli re-arm kenarıyla controlled-stop validator kabulü
  geri geldi;
- stream durduğunda heartbeat-stale reject `6` ile link tekrar fail-closed
  düştü.

PLC restart/replay koruması bu kontrollü fiziksel kabul testini geçmiştir.

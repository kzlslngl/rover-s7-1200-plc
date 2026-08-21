# Orin Command Validator V0.6 Fiziksel Kabul — 21 Ağustos 2026

Bu belge Ana Proje Codex'i tarafından, fiziksel PLC'ye yüklenmiş
`FB_OrinCommandSnapshotValidator V0.6` için yapılan Modbus TCP kabul testinin
kanıtı olarak hazırlanmıştır.

Ana proje kaynak otoritesi:

`rover-core-ros2/agent/local-metric-map@854fee6f67ad3cb37f526c84fbcf79cdcacf10fa`

## Güvenlik sınırı ve topoloji

| Alan | Değer |
|---|---|
| PLC | `192.168.2.100:502`, S7-1200 CPU 1214C |
| VM | `192.168.2.10/24` |
| Protokol | Modbus TCP, unit ID `1`, protokol `1.1` |
| Komut | Tek FC16, offset `0`, quantity `64` |
| State | Aynı TCP session içinde FC03, offset `64`, quantity `64` |
| İstek sahibi | Tek fiziksel Modbus client |
| Komut modu | Yalnız `SAFE_DISABLED` |
| Command flags | `COMMAND_VALID = 0x0001` |
| Hız/direksiyon hedefi | `0.0 m/s`, `0.0 rad` |
| AUTO | Hiç gönderilmedi |

Ana Test 1–7 serisi boyunca aynı açık TCP session kullanıldı. Her çevrim tek
FC16 yazımı ve ardından aynı session üzerinden FC03 state okuması yaptı.
Session re-arm beklenirken de güvenli snapshot sayaçları ilerletildi.

Test 2'nin ilk çalışmasında terminal giriş kuyruğu nedeniyle
`SessionRearm=TRUE` ön koşulunun kullanıcı tarafından tam olarak ne zaman
uygulandığı kesin kanıtlanamadı. Bu nedenle Test 2, tamamen yeni session ile
ikinci ve ayrı bir kalıcı TCP bağlantısında baştan tekrarlandı. Aşağıdaki Test 2
sonucu bu temiz tekrardan alınmıştır. Hiçbir anda iki Modbus client eşzamanlı
çalışmadı.

PLC state içindeki `ORIN_COMMAND_LINK_VALID` status biti bu raporda
`DataValid` olarak gösterilmiştir. Validator içindeki `HeartbeatFresh` yerel
tag'i FC03 state sözleşmesinde ayrı alan değildir; heartbeat testi
`RejectReason`, link-valid biti ve accepted command'ın ilerlememesi üzerinden
dışarıdan doğrulanmıştır.

Tüm ölçümlerde:

- `operational_state = 3 (MANUAL)`;
- `active_authority = 1 (MANUAL)`;
- `actual_speed_mps = 0.0`;
- `fault_bits = 0`;
- fiziksel hareket oluşmadı.

PLC'nin yayımladığı direksiyon feedback değeri test boyunca yaklaşık
`-0.010571476 rad` idi. Gönderilen direksiyon hedefi her zaman `0.0 rad` kaldı.

## Sonuç özeti

| Test | Beklenen | Fiziksel sonuç | Karar |
|---|---|---|---|
| 1. Normal regresyon/re-arm | Yeni session `5`, taze darbe sonrası kabul | `5 -> 0`, accepted session/command ilerledi | Geçti |
| 2. Re-arm önceden TRUE | Held TRUE yeni session'ı kabul etmemeli | Eski session korundu; taze darbe sonrası kabul | Geçti |
| 3. Duplicate snapshot | `8`, invalid; ileri snapshot ile recovery | `8 -> 0` | Geçti |
| 4. Backward snapshot | `8`, invalid | `8 -> 0` recovery | Geçti |
| 5. Backward heartbeat | `8`, heartbeat fresh sayılmamalı | `8`, accepted command sabit; recovery `0` | Geçti |
| 6. UInt32 wrap | `FFFFFFFE -> FFFFFFFF -> 0 -> 1` kabul | Dört adımın tamamı `0` ve valid | Geçti |
| 7. Frozen command | Timeout sonrası `7`; ileri command ile recovery | `7 -> 0` | Geçti |

## Ölçülen snapshot/state kanıtı

Ondalık session kimliklerinin karşılıkları:

- `1627389953 = 0x61000001`
- `1627389954 = 0x61000002`
- `1627389958 = 0x61000006`
- `1627389986 = 0x61000022`

`PLC seq/hb`, FC03 state bloğunun begin sequence ve PLC heartbeat değeridir.
`Accepted`, `accepted_orin_session_id / accepted_command_sequence` çiftidir.

| Aşama | Gönderilen session | Snap / HB / Cmd | PLC seq/hb | DataValid | Reject | Rearm | Accepted | Status / interlock |
|---|---:|---|---|---|---:|---|---|---|
| T1 yeni session | `1627389953` | `104 / 104 / 104` | `417167 / 417167` | Hayır | `5` | Evet | `0 / 1535` | `0x0502 / 0x00008000` |
| T1 taze darbe sonrası | `1627389953` | `563 / 563 / 563` | `419310 / 419310` | Evet | `0` | Hayır | `1627389953 / 563` | `0x0702 / 0` |
| T2 held TRUE, yeni session | `1627389986` | `2010 / 2010 / 2010` | `426037 / 426037` | Hayır | `5` | Evet | `1627389958 / 2` | `0x0502 / 0x00008000` |
| T2 taze darbe sonrası | `1627389986` | `2234 / 2234 / 2234` | `427058 / 427058` | Evet | `0` | Hayır | `1627389986 / 2234` | `0x0702 / 0` |
| T3 duplicate snapshot | `1627389954` | `1423 / 1424 / 1424` | `422181 / 422181` | Hayır | `8` | Hayır | `1627389954 / 1423` | `0x0502 / 0` |
| T3 recovery | `1627389954` | `1424 / 1425 / 1425` | `422184 / 422184` | Evet | `0` | Hayır | `1627389954 / 1425` | `0x0702 / 0` |
| T4 backward snapshot | `1627389954` | `1423 / 1426 / 1426` | `422188 / 422188` | Hayır | `8` | Hayır | `1627389954 / 1425` | `0x0502 / 0` |
| T4 recovery | `1627389954` | `1425 / 1427 / 1427` | `422191 / 422191` | Evet | `0` | Hayır | `1627389954 / 1427` | `0x0702 / 0` |
| T5 backward heartbeat | `1627389954` | `1426 / 1426 / 1428` | `422195 / 422195` | Hayır | `8` | Hayır | `1627389954 / 1427` | `0x0502 / 0` |
| T5 recovery | `1627389954` | `1427 / 1428 / 1429` | `422198 / 422198` | Evet | `0` | Hayır | `1627389954 / 1429` | `0x0702 / 0` |
| T6 yeni wrap session | `1627389958` | `FFFFFFFD / FFFFFFFD / FFFFFFFD` | `422201 / 422201` | Hayır | `5` | Evet | `1627389954 / 1429` | `0x0502 / 0x00008000` |
| T6 wrap `FFFFFFFE` | `1627389958` | `FFFFFFFE / FFFFFFFE / FFFFFFFE` | `423252 / 423252` | Evet | `0` | Hayır | `1627389958 / FFFFFFFE` | `0x0702 / 0` |
| T6 wrap `FFFFFFFF` | `1627389958` | `FFFFFFFF / FFFFFFFF / FFFFFFFF` | `423257 / 423257` | Evet | `0` | Hayır | `1627389958 / FFFFFFFF` | `0x0702 / 0` |
| T6 wrap `00000000` | `1627389958` | `0 / 0 / 0` | `423260 / 423260` | Evet | `0` | Hayır | `1627389958 / 0` | `0x0702 / 0` |
| T6 wrap `00000001` | `1627389958` | `1 / 1 / 1` | `423265 / 423265` | Evet | `0` | Hayır | `1627389958 / 1` | `0x0702 / 0` |
| T7 frozen command | `1627389958` | `3 / 3 / 1` | `423275 / 423275` | Hayır | `7` | Hayır | `1627389958 / 1` | `0x0502 / 0` |
| T7 recovery | `1627389958` | `4 / 4 / 2` | `423277 / 423277` | Evet | `0` | Hayır | `1627389958 / 2` | `0x0702 / 0` |

Her command snapshot doğru header, reserved-zero alanlar, eş begin/end
sequence ve yeniden hesaplanmış CRC-32/ISO-HDLC ile tek FC16 isteğinde
gönderildi. Backward snapshot testi de doğru CRC taşıdığı için rejection'ın CRC
değil progression kontrolünden geldiği doğrulandı.

## Ayrıntılı kararlar

### Test 1 — Normal regresyon

Yeni `0x61000001` session başlangıçta kabul edilmedi. PLC
`RejectReason=5 (SESSION_CHANGED_REARM_REQUIRED)` ve re-arm interlock bitini
üretti. Session görüldükten sonra TIA üzerinden manuel `FALSE -> TRUE -> FALSE`
darbesi uygulandı. PLC aynı kalıcı TCP session içindeki ilerleyen güvenli
snapshot'ı kabul etti; link-valid biti ve accepted session/command birlikte
ilerledi.

### Test 2 — Held-TRUE yarış koruması

PLC'de `SessionRearm` önceden TRUE yapılıp TRUE seviyesinde tutulduktan sonra
tamamen yeni `0x61000022` session başlatıldı. On ilerleyen snapshot sonunda
yeni session kabul edilmedi; accepted session/command eski
`0x61000006 / 2` değerinde kaldı. Re-arm önce FALSE yapılıp yeni bir
`FALSE -> TRUE -> FALSE` darbesi uygulandığında session kabul edildi. V0.6'nın
held-TRUE/same-scan koruması fiziksel olarak doğrulandı.

### Test 3–5 — Progression reddi ve recovery

- Duplicate snapshot sırasında heartbeat ve command ilerlemesine rağmen
  snapshot `1423` tekrarlandı; reject `8` oldu.
- Backward snapshot `1424` kabulünden sonra `1423` olarak, doğru CRC ile
  gönderildi; reject `8` oldu.
- Backward heartbeat testinde snapshot `1426`, command `1428` iken heartbeat
  önceki kabul edilen `1427` değerinden `1426` değerine götürüldü. Reject `8`
  oldu ve accepted command `1427` değerinde kaldı.
- Her testten sonra bütün sayaçların gerçek ileri değeriyle link-valid ve
  reject `0` recovery görüldü.

### Test 6 — Modulo-2^32 wrap

Yeni `0x61000006` session re-arm edildikten sonra snapshot sequence, heartbeat
ve command sequence birlikte aşağıdaki sırada gönderildi:

```text
0xFFFFFFFE -> 0xFFFFFFFF -> 0x00000000 -> 0x00000001
```

Dört snapshot'ın tamamı yeni/ileri kabul edildi. Accepted command sequence her
adımı birebir izledi; wrap sırasında reject veya link-valid düşüşü oluşmadı.

### Test 7 — Frozen command

Wrap sonrası command sequence `1` değerinde tutulurken snapshot sequence ve
heartbeat ilerletildi. PLC command timeout sonunda reject `7 (COMMAND_STALE)`
ve link invalid üretti; accepted command `1` kaldı. Command `2` gönderildiğinde
aynı session içinde reject `0` ve link-valid recovery görüldü.

## Test sonrası güvenli durum

Test client'ı kapatıldıktan sonra ayrı bir salt-okunur FC03 kontrolünde:

| Alan | Son değer |
|---|---:|
| PLC state sequence | `427620` |
| Operational state / authority | `3 / 1` — MANUAL |
| Status flags | `0x0502` — command link invalid |
| Reject reason | `6 (HEARTBEAT_STALE)` |
| Fault / interlock | `0 / 0` |
| Accepted session / command | `1627389986 / 2234` |
| Actual speed | `0.0 m/s` |

Bu, istemci durduğunda accepted kimliğin tanı amacıyla korunmasına rağmen
heartbeat freshness'in hareket iznini düşürdüğünü doğrular.

## Nihai kabul

Fiziksel PLC'deki `FB_OrinCommandSnapshotValidator V0.6`, istenen yedi testin
tamamını geçti:

- re-arm yeni ve bilinçli kenar gerektirir;
- held TRUE yeni session'ı otomatik kabul etmez;
- duplicate/backward snapshot ve backward heartbeat fail-closed reddedilir;
- uint32 wrap ileri progression olarak kabul edilir;
- command donması bağımsız timeout ile reddedilir;
- geçerli ileri veriyle kontrollü recovery mümkündür.

Bu kabul yalnız Orin command validator ve Modbus haberleşme katmanını kapsar.
AUTO hareket izni, gerçek aktüatör, fren, odometry/encoder ve saha güvenlik
kabulü bu testin kapsamı dışındadır ve kapalı kalır.

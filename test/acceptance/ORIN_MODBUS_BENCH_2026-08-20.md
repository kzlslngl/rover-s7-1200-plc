# Orin–PLC Modbus TCP Bench Testi — 2026-08-20

## Düzen

- CPU: Siemens S7-1200 CPU 1214C DC/DC/DC (`6ES7 214-1AG40-0XB0`)
- CPU firmware: V4.6
- PLC bench IP: `192.168.2.100/24`
- Modbus TCP port: `502`
- Unit ID: `1`
- Raw DB: `DB_ModbusServerRaw.Holding[0..319]`
- Command wire offset: `0`, quantity `64`
- Protocol: `1.1`

## MB_SERVER compile ve idle durumu

`FB_OrinModbusServer` ve instance DB TIA Portal'da `0 error / 0 warning`
ile derlendi.

Online idle gözlemi:

- `Enable = TRUE`
- `Error = FALSE`
- `Status = 16#7002`
- raw ve staging command alanları başlangıçta sıfır

Sonuç: **PASS**

## PLC state typed staging ve canlı alan testi

Manuel authority aktifken typed model ve FC03 wire görüntüsü karşılaştırıldı:

- `OperationalState = 3` (`MANUAL`)
- `ActiveAuthority = 1` (`MANUAL`)
- `StatusFlags = 16#0502` (steering angle, manual signal ve G16 valid)
- `FaultBits = 0`, `InterlockBits = 0`
- `G16SummaryFlags = 16#0069`
- `SafetySummaryFlags = 16#0002`
- steering feedback `0.0104600 rad`
- begin/end sequence `16#0001_92B1`
- wire CRC `16#A4FA_0284`
- PC bağımsız CRC `16#A4FA_0284`

Ortak servo-enable çıkışı gerçek propulsion-drive feedback olmadığı için
`DRIVE_ENABLED` status biti bilinçli olarak kapalı tutuldu.

Sonuç: **PASS**

## FC03 bağlantı ve adresleme testi

PC'den PLC `192.168.2.100:502` adresine wire offset `0`, quantity `16`
FC03 isteği gönderildi.

Gözlenen sonuç:

- FC03 cevabı başarılı
- 16 register okundu
- başlangıç değerlerinin tamamı `16#0000`

Sonuç: **PASS**

## Ortak command known-result FC16 testi

Ana protokol commit `caba72c` içindeki `command_snapshot` vektörü tek FC16
ile wire offset `0`, quantity `64` olarak yazıldı.

Beklenen temel değerler:

- begin/end sequence: `42`
- Orin session: `16#0102_0304`
- heartbeat: `100`
- command sequence: `99`
- requested mode: `3` (`CONTROLLED_STOP`)
- command flags: `16#0005`
- CRC: `16#5C22_4D43`

PLC gözlemi:

- `SnapshotValid = TRUE`
- `RejectReason = 0`
- `CalculatedCrc = WireCrc = 16#5C22_4D43`
- `TargetSpeedMps = 0.0`
- `TargetSteeringAngleRad = -0.25`
- `AccelerationLimitMps2 = 0.5`
- `DecelerationLimitMps2 = 1.25`
- `SteeringRateLimitRadps = 0.4`
- `MissionSpeedLimitMps = 2.0`
- `CommandValidityMs = 250`
- `CommandValid = TRUE`
- `ControlledStopRequest = TRUE`

Integer, big-endian word order ve IEEE-754 Real decode değerleri ana vektörle
birebir eşleşti.

Diagnostics-only güvenlik kapısı gereği:

- `DB_ValidatedOrinCommand.Data.Valid = FALSE`
- command hiçbir authority veya actuator girişine bağlı değil

Sonuç: **PASS**

## Sonraki kapılar

- PLC state/G16/diagnostics/active-config publisher blokları
- output write-violation detection

## Orin session ve re-arm testi

Geçerli controlled-stop snapshot'ları 100 ms aralıkla, artan heartbeat ve
command sequence ile gönderildi.

- yeni session: `16#1122_3344`
- re-arm öncesi `SessionRearmRequired = TRUE`
- re-arm öncesi `RejectReason = 5`
- re-arm girişine `FALSE -> TRUE -> FALSE` darbesi verildi
- re-arm sonrası `SessionRearmRequired = FALSE`
- re-arm sonrası `RejectReason = 0`
- `HeartbeatFresh = TRUE`
- `CommandFresh = TRUE`

Akış kesildikten sonra her iki watchdog timeout oldu ve son öncelikli sonuç
`RejectReason = 6` (`HEARTBEAT_STALE`) olarak gözlendi.

Sonuç: **PASS**

## PLC boot/session testi

`DB_PlcBootRetain.BootCounter` retentive, session manager instance state'i ve
`DB_PlcSessionStatus` non-retentive yapılandırıldı.

İlk startup:

- `Initialized = TRUE`
- `BootCounter = 16#0000_0001`
- `PlcSessionId = 16#0000_0001`

Program yeniden download edilmeden CPU gücü kesilip tekrar verildi.

İkinci startup:

- `Initialized = TRUE`
- `BootCounter = 16#0000_0002`
- `PlcSessionId = 16#0000_0002`

Session sıfırdan farklıdır ve her CPU boot'unda değişmiştir. `NewSessionPulse`
yalnız ilk OB1 scan'inde üretildiğinden online watch ekranında FALSE görülmesi
beklenir.

Sonuç: **PASS**

## Payload finite/range/mode negatif testleri

Her testte heartbeat ve command sequence ilerletildi, paket CRC'si yeniden
hesaplandı ve session re-arm tamamlandı.

| Test | Gözlenen sonuç |
|---|---|
| Geçerli controlled-stop payload | `PayloadValid=TRUE`, `RejectReason=0` |
| Steering IEEE-754 NaN | `PayloadValid=FALSE`, `RejectReason=9` |
| Target speed `3.0`, üst sınır `2.0` | `PayloadValid=FALSE`, `RejectReason=10` |
| Reserved command flag `16#0080` set | `PayloadValid=FALSE`, `RejectReason=3` |
| `CommandValidityMs=600`, üst sınır `500` | `PayloadValid=FALSE`, `RejectReason=10` |

Bütün negatif testlerde `CalculatedCrc = WireCrc` ve freshness sonuçları TRUE
kaldı. Böylece red nedeninin transport/CRC değil doğrudan payload guard olduğu
kanıtlandı.

Sonuç: **PASS**

## Yapısal negatif snapshot testleri

| Test | CRC durumu | Gözlenen sonuç |
|---|---|---|
| Wire CRC son biti değiştirilmiş | eşit değil | `RejectReason=4` |
| Protocol `1.0` | eşit | `RejectReason=2` |
| Begin/end sequence farklı | eşit | `RejectReason=3` |
| Reserved register `30=1` | eşit | `RejectReason=3` |

Yapısal olarak reddedilen snapshot'lar yeni session kabulü veya re-arm
oluşturmadı. Eski session watchdog timeout'ları son yapısal red nedeninin
üstünü örtmedi.

Sonuç: **PASS**

## Atomik typed kabul ve command-validity timeout

Geçerli controlled-stop akışı, session re-arm sonrası:

- `HeartbeatFresh = TRUE`
- `CommandFresh = TRUE`
- `PayloadValid = TRUE`
- `CommandValidityFresh = TRUE`
- `DataValid = TRUE`
- `RejectReason = 0`
- `DB_ValidatedOrinCommand.Data.Valid = TRUE`

Accepted typed payload yalnız bütün kontrolleri geçen yeni command sequence
için tek UDT atamasıyla güncellendi. Bench aşamasında yalnız
`SAFE_DISABLED` ve `CONTROLLED_STOP` kabul edilebilir; AUTO kapalıdır.

Akış kesildikten sonra:

- `CommandFresh = FALSE`
- `CommandValidityFresh = FALSE`
- `HeartbeatFresh = FALSE`
- `DataValid = FALSE`
- `DB_ValidatedOrinCommand.Data.Valid = FALSE`
- son öncelikli `RejectReason = 6` (`HEARTBEAT_STALE`)

Son kabul edilmiş sayısal payload korunurken `Valid=FALSE` olması beklenen
fail-silent davranıştır.

Sonuç: **PASS**

## Bağımsız command-sequence freshness testi

Yeni session altında snapshot sequence ve heartbeat ilerletilirken command
sequence sabit tutuldu:

- session: `16#2233_4455`
- command sequence: `1`, sabit
- re-arm tamamlandı
- `HeartbeatFresh = TRUE`
- `CommandFresh = FALSE`
- `RejectReason = 7` (`COMMAND_STALE`)
- CRC doğrulaması devam etti

Bu test TCP bağlantısı, FC16 trafiği ve heartbeat sağlıklı olsa bile donmuş
command sequence'in ayrı olarak reddedildiğini doğruladı.

Sonuç: **PASS**

## PLC_TO_ORIN_STATE canlı publisher testi

- Publisher periyodu: `20 ms`
- FC03 okuması: holding register `64..127` (`64` register)
- Başlık: magic `16#5253`, protokol `1.1`, uzunluk `64`
- PLC session: `16#0000_0002`
- Begin sequence: `16#0000_0B3C`
- End sequence: `16#0000_0B3C`
- Wire CRC: `16#FBAB_A5D8`
- PC üzerinde bağımsız hesaplanan CRC: `16#FBAB_A5D8`
- Atomik sequence kontrolü: **PASS**
- CRC kontrolü: **PASS**

Sonuç: **PASS**

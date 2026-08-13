# ESP Modbus TCP Bench Devreye Alma

## Bağlantı profili

| Parametre | Geçici bench değeri |
|---|---:|
| PLC | `192.168.2.100/24` |
| ESP | `192.168.2.166/24` |
| TCP port | `502` |
| Unit ID | `1` |
| Fonksiyon | FC03 |
| Wire başlangıç offset'i | `320` (`0x0140`) |
| Siemens `MB_DATA_ADDR` | `40321` |
| Uzunluk | `64` WORD |

`MB_DATA_ADDR=40321`, Siemens'in holding-register gösterimidir. ESP'ye giden
Modbus TCP PDU içindeki gerçek sıfır tabanlı başlangıç adresi `320`'dir.

## TIA Portal V20 import ve çağrı

1. CPU'yu `6ES7 214-1AG40-0XB0`, firmware V4.6 olarak yapılandır.
2. CPU PROFINET adresini geçici olarak `192.168.2.100/24` yap.
3. Önce `exported/db/DB_EspGatewayRx.scl` kaynağını import edip derle.
4. Sonra `exported/blocks/FB_EspGatewayClient.scl` kaynağını import edip derle.
5. FB için bir instance DB oluştur.
6. `InterfaceId` girişine CPU'nun PROFINET interface system constant değerini
   bağla; sayısal HW ID'yi kaynakta sabitleme.
7. Bu `MB_CLIENT` sürümünde çevrimsel okuma için `Enable=TRUE` ve
   `Request=TRUE` tutulabilir. Blok `BUSY` durumunu kendi içinde yönetir.
8. Watch table'da `Done`, `Busy`, `Error`, `Status` ve
   `DB_EspGatewayRx.Registers[0..63]` alanlarını izle.

TIA Portal V20'de `TCON_IP_v4.RemoteAddress`, `IP_V4` tipindedir. IPv4
oktetlerine `RemoteAddress.ADDR[1..4]` üzerinden erişilir; doğrudan
`RemoteAddress[1..4]` kullanımı geçersizdir.

İlk başarılı okumada beklenen ham kontroller:

- `Registers[0] = 16#4547`
- `Registers[1] = 1`
- `Registers[2] = 1`
- `Registers[3] = 64`
- `Registers[4..5]` ile `Registers[62..63]` aynı sequence değerini vermeli
- `Registers[15]` sağlıklı SBUS için bit 0 ve bit 3 set olmalı

Ham buffer doğrudan kontrol veya aktüatör hesabında kullanılmayacaktır. CRC,
sequence, session, heartbeat, freshness ve flags validator'ı tamamlanana kadar
bu entegrasyon yalnızca watch/diagnostics amaçlıdır.

## Snapshot validator import ve çağrı

Aşağıdaki sırayla import edip her adımdan sonra compile et:

1. `exported/udt/UDT_G16ValidatedInput.scl`
2. `exported/db/DB_ValidatedG16Input.scl`
3. `exported/blocks/FC_ReadU32BigEndian.scl`
4. `exported/blocks/FC_Crc32IsoHdlc.scl`
5. `exported/blocks/FB_G16SnapshotValidator.scl`

OB1'de validator için ayrı instance DB oluştur ve şu değerlerle çağır:

```text
PollDone                := FB_EspGatewayClient.Done
PollError               := FB_EspGatewayClient.Error
Raw                     := DB_EspGatewayRx.Registers
MaxFrameAgeMs           := 100
PollTimeout             := T#500ms
RequiredHealthySnapshots := 3
```

İzlenecek temel alanlar:

- `DataValid`: üç ardışık sağlıklı snapshot sonrasında `TRUE`
- `RejectBits`: sağlıklı durumda `16#0000`
- `CalculatedCrc = WireCrc`
- `HealthySnapshotCount = 3`
- `DB_ValidatedG16Input.Data.Valid = TRUE`
- `DB_ValidatedG16Input.Data.ChannelRaw[0..15]`: yalnızca kabul edilmiş veri

`RejectBits` anlamı:

| Bit | Maske | Neden |
|---:|---:|---|
| 0 | `16#0001` | Modbus error veya poll timeout |
| 1 | `16#0002` | Magic/version/length hatası |
| 2 | `16#0004` | Torn veya geriye giden sequence |
| 3 | `16#0008` | CRC uyuşmazlığı |
| 4 | `16#0010` | Heartbeat ilerlemiyor |
| 5 | `16#0020` | SBUS valid/alive/lost/failsafe/fault hatası |
| 6 | `16#0040` | Kanal sayısı/maskesi veya frame age hatası |
| 7 | `16#0080` | Reserved register sıfır değil |

Validator `DataValid=TRUE` üretse bile bu aşamada veri aktüatörlere
bağlanmayacaktır. Kanal mapping, neutral/deadband kalibrasyonu ve authority
state machine ayrı güvenlik kapılarıdır.

PLC, ESP'nin snapshot üretiminden hızlı poll yaparsa aynı sequence tekrar
okunabilir. Byte-identical duplicate snapshot hata değildir: kabul sayacını
artırmaz, fakat son geçerli veri `PollTimeout` dolana kadar korunur.

## 2026-08-13 canlı ESP kanıtı

PC üzerinden `192.168.2.166:502` için tam FC03 testi başarılıdır:

- 64 register alındı
- magic `16#4547`, protokol `1.1`
- begin/end sequence eşleşti
- CRC-32/ISO-HDLC eşleşti
- `frame_age_ms=0`, `flags=16#0009`
- FC06 yazma isteği illegal-function exception ile reddedildi

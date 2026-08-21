# Orin–PLC Modbus TCP Devreye Alma

## Wire alanı

PLC `MB_SERVER` için tek raw alan kullanır:

| Raw index | Blok | Sahip | İşlem |
|---:|---|---|---|
| `0..63` | `ORIN_TO_PLC_COMMAND` | Orin | tek FC16 write |
| `64..127` | `PLC_TO_ORIN_STATE` | PLC | tam FC03 read |
| `128..191` | `G16_STATUS` | PLC | tam FC03 read |
| `192..255` | `PLC_DIAGNOSTICS` | PLC | tam FC03 read |
| `256..319` | `ACTIVE_CONFIG` | PLC | tam FC03 read |

`DB_ModbusServerRaw` global, non-optimized ve non-retentive kalmalıdır. Raw
register'lar safety, authority veya actuator hesabında doğrudan kullanılmaz.

`G16_STATUS.channel_normalized[16]` signed `Int` kullanır ve nominal ölçeği
`-1000..+1000`'dir. Negatif değerler Modbus Word üzerinde iki'nin tümleyeni
olarak encode edilir. Canlı kalibrasyon staging'i tamamlanana kadar bu dizi
sıfır yayınlanır; ham kanallar ve validity alanları ayrı kalır.

İlk canlı `FC_StageG16StatusModel` yalnız doğrulanmış ESP snapshot'ındaki
session, heartbeat, SBUS frame counter/age/flags, channel mask ve 16 ham
kanalı taşır. `CHANNEL_CALIBRATION_VALID`, `LINK_QUALITY_VALID` ve
`RSSI_VALID` bu geçiş aşamasında kapalı kalır.

PLC state ve G16 status publisher V0.2 zamanlaması IEC `TON` kullanır.
`PublishPeriodMs=20` gerçek OB1 scan süresinden bağımsız eşik oluşturur;
hard-coded `CycleTimeMs` girişi kaldırılmıştır. PLC state içindeki monotonic
alan configured nominal publish period ile ilerleyen diagnostic değerdir ve
safety/freshness hesabında kullanılmaz.

`FB_CycleTimeMonitor` OB1'in ilk network'inde her scan çağrılır. Siemens
`RUNTIME` CPU iç sayacını kullanarak aynı statik `LReal` memory ile ardışık
çağrılar arasındaki süreyi saniye cinsinden ölçer. Çıkış `CycleTimeSec`, scan
tabanlı rate/acceleration integratörlerine verilir. İlk veya configured üst
sınırı aşan örnekte yalnız commissioning fallback değeri kullanılır ve
`InvalidSampleCount` artırılır.

## İlk import sırası

1. `exported/udt/UDT_OrinCommandValidated.scl`
2. `exported/udt/UDT_CommandValidationStatus.scl`
3. `exported/db/DB_ModbusServerRaw.scl`
4. `exported/db/DB_OrinCommandStagingRaw.scl`
5. `exported/db/DB_ValidatedOrinCommand.scl`
6. `exported/db/DB_OrinCommandValidation.scl`
7. `exported/blocks/FC_StageOrinCommand.scl`
8. `exported/blocks/FB_OrinModbusServer.scl`
9. `exported/blocks/FC_ReadReal32BigEndian.scl`
10. `exported/blocks/FC_IsFiniteReal32BigEndian.scl`
11. `exported/blocks/FB_OrinCommandSnapshotValidator.scl`

Her dosyadan sonra compile yapılır. `DB_ModbusServerRaw` özelliklerinde
optimized access kapalı, retain kapalı ve `Holding[0..319]` olduğu ayrıca
TIA ekranından doğrulanır.

## OB1 sahiplik sırası

İlk aşamada fiziksel çıkış veya authority bağlantısı yapılmaz:

1. fiziksel input mirror;
2. `FB_OrinModbusServer` çağrısı;
3. `FC_StageOrinCommand()`;
4. command validator (bir sonraki teslim);
5. mevcut G16 ve authority akışı.

`FC_StageOrinCommand`, raw command alanını her scan bir kez staging DB'ye
kopyalar. Sonraki doğrulama çevrimi yalnız staging DB'yi okur.

## İlk MB_SERVER çağrısı

`FB_OrinModbusServer` için ayrı instance DB oluştur. OB1 çağrısı:

```text
Enable      := TRUE
InterfaceId := CPU PROFINET interface system constant
```

Wrapper passive TCP kullanır:

```text
Connection ID = 16#0002
LocalPort     = 502
RemoteAddress = 0.0.0.0
RemotePort    = 0
```

Connection ID `1`, ESP `MB_CLIENT` tarafından kullanıldığı için server'da
`2` seçilmiştir. Aynı CPU interface'inde başka bir server için port `502`
kullanılmamalıdır.

İlk watch alanları:

```text
NewDataReady
DataRead
Error
Status
DB_ModbusServerRaw.Holding[0..15]
```

`NewDataReady`, Modbus client raw holding register alanına yazdığında bir scan
darbe verir. `DataRead`, client alanı okuduğunda bir scan darbe verir. Bu
sinyaller freshness veya hareket izni değildir.

## Güvenlik durumu

Bu ilk iskelet diagnostics/watch amaçlıdır. `DB_ValidatedOrinCommand.Data`
henüz hiçbir authority veya actuator girişine bağlanmaz. `MB_SERVER` bağlantı
durumu veya başarılı FC16 yazımı hareket izni değildir.

## Diagnostics-only snapshot validator

`FB_OrinCommandSnapshotValidator` şu kontrolleri yapar:

- magic ve block length;
- begin/end sequence eşitliği;
- reserved `30..59` sıfır kontrolü;
- tam protocol `1.1` eşleşmesi;
- CRC-32/ISO-HDLC;
- big-endian integer ve IEEE-754 Real decode.
- Orin session değişimi ve yükselen-kenar re-arm;
- heartbeat progression için PLC-local watchdog;
- command-sequence progression için PLC-local watchdog.

V0.2 çağrı başlangıç değerleri:

```text
SessionRearm     := test_session_rearm // yalnız FALSE->TRUE darbesi
HeartbeatTimeout := T#500ms
CommandTimeout   := T#250ms
LimitsValid             := TRUE // yalnız bench için
MaxCommandValidityMs    := 500
MaxForwardSpeedMps      := 2.0
MaxReverseSpeedMps      := 1.0
MaxSteeringAngleRad     := 0.6
MaxAccelerationMps2     := 2.0
MaxDecelerationMps2     := 3.0
MaxSteeringRateRadps    := 1.0
MaxMissionSpeedMps      := 2.0
```

Yeni bir session ilk görüldüğünde `SessionRearmRequired=TRUE` ve
`RejectReason=5` olur. Re-arm girişinin önceden TRUE tutulması gelecekteki
session'ı kabul etmez; session görüldükten sonra yeni bir yükselen kenar
gereklidir. Heartbeat timeout `RejectReason=6`, command timeout
`RejectReason=7` üretir.

V0.3 ayrıca altı Real alanında NaN/Infinity, requested-mode/command-flags
tutarlılığı ve bench limitlerine göre range kontrolü yapar. Sonuç
`PayloadValid` çıkışında görülür. Bu aşamada payload decode DB'ye yazılsa da
`DB_ValidatedOrinCommand.Data.Valid` güvenlik gereği hâlâ `FALSE` kalır.

V0.5 accepted typed DB'yi yalnız tamamen geçen yeni command sequence için tek
UDT atamasıyla atomik günceller. `CommandValidityMs` ayrı PLC-local TON ile
uygulanır. Bu bench aşamasında yalnız `SAFE_DISABLED` ve `CONTROLLED_STOP`
mode'ları `DataValid=TRUE` olabilir; AUTO mode'ları autonomy/safety guard
entegrasyonu tamamlanana kadar `RejectReason=11` ile kapalıdır.

## PLC boot/session manager

Import sırası:

1. `exported/udt/UDT_PlcSessionStatus.scl`
2. `exported/db/DB_PlcBootRetain.scl`
3. `exported/db/DB_PlcSessionStatus.scl`
4. `exported/blocks/FB_PlcSessionManager.scl`

`DB_PlcBootRetain.BootCounter` retentive olmalıdır. Import sonrasında TIA
özelliklerinde optimized access açık ve boot counter Retain seçili olduğu
ayrıca doğrulanır. `DB_PlcSessionStatus` ve `FB_PlcSessionManager` instance
state'i non-retentive kalır.

`FB_PlcSessionManager` OB1'in ilk communication network'lerinden önce her scan
çağrılır. İlk startup scan'inde retentive counter bir artırılır; wrap sonucu
sıfır oluşursa `1` kullanılır. Session değeri bu boot counter'dır ve daima
sıfırdan farklıdır. Program download sırasında retentive DB yeniden initialize
edilirse önceki commissioning session geçmişi korunmayabilir; normal CPU
restart testi download yapmadan yürütülür.

## PLC state publisher typed model

`UDT_PlcStateModel` wire offset `64..111` alanlarının typed kaynağıdır.
`DB_PlcStateModel` non-retentive kalır ve raw register dizilimini kontrol
mantığına taşımaz. `DB_ExpectedPublishedRaw.Registers[64..319]`, PLC-owned dört
output bloğunun beklenen görüntüsünü tutar; ileride dış yazma ihlali bu görüntü
ile `DB_ModbusServerRaw.Holding[64..319]` karşılaştırılarak algılanacaktır.

`FC_StagePlcStateModel` yalnız mevcut ve anlamı doğrulanmış typed kaynakları
state modeline taşır. Henüz fiziksel feedback/calibration bulunmayan speed,
throttle, brake ve wheel-speed alanları sıfır kalır; bunların `StatusFlags`
validity bitleri açılmaz. Ortak servo-enable çıkışı gerçek propulsion-drive
enable geri bildirimi sayılmaz; `DRIVE_ENABLED` biti şimdilik kapalıdır.
Bench'teki tek birleşik E-stop/safety-chain girişi,
ayrı safety rölesi geri bildirimi eklenene kadar safety özetinin iki ilgili
anlamını birlikte temsil eder.

Blok `SnapshotValid=TRUE` üretse bile
`DB_ValidatedOrinCommand.Data.Valid=FALSE` bırakır. Session re-arm,
heartbeat/command freshness, finite/range, safety ve autonomy guard'ları
tamamlanmadan bu typed command hareket kaynağı değildir.

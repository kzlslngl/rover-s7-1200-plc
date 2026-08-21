# G16 Frame Freshness Bench Testi — 2026-08-20

## Düzen

- CPU: Siemens S7-1200 CPU 1214C DC/DC/DC (`6ES7 214-1AG40-0XB0`)
- CPU firmware: V4.6
- PLC bench IP: `192.168.2.100/24`
- ESP bench IP: `192.168.2.166/24`
- Validator: `FB_G16SnapshotValidator` V0.2
- `MaxFrameAgeMs`: `100`
- `G16FrameTimeout`: `T#250ms`
- `PollTimeout`: `T#2s`
- `RequiredHealthySnapshots`: `3`

## Sağlıklı haberleşme

Gözlenen sonuç:

- `DataValid = TRUE`
- `FrameCounterFresh = TRUE`
- `RejectBits = 16#0000`
- `HealthySnapshotCount = 3`
- `CalculatedCrc = WireCrc`
- `SbusFrameCounter` ilerliyor

Sonuç: **PASS**

## Validator V0.3 ileri-sayaç regresyonu — 21 Ağustos 2026

`FC_IsDWordForward` ve `FB_G16SnapshotValidator V0.3` TIA V20'de sifir hata,
sifir warning ile derlenip fiziksel CPU'ya yuklendi. Normal ESP/SBUS akisinda:

- `DataValid = TRUE`
- `FrameCounterFresh = TRUE`
- `RejectBits = 16#0000`
- `HealthySnapshotCount = 3`
- `SessionId = 16#44AC_7D53` sabit
- snapshot sequence, heartbeat ve SBUS frame counter ilerliyor

SBUS hatti fiziksel olarak ayrildiginda ESP session, Ethernet, snapshot
sequence ve heartbeat calismaya devam etti; SBUS frame counter ilerlemesi
durdu. PLC-local `G16FrameTimeout = T#250MS` sonrasinda:

- `DataValid = FALSE`
- `FrameCounterFresh = FALSE`
- `HealthySnapshotCount = 0`
- `RejectBits = 16#0101`

`16#0100` SBUS frame-counter freshness/anomaly bitidir. Hat uzun sure ayrik
kaldigi icin kabul edilebilir yeni snapshot watchdog'u da dolmus ve
`16#0001` ile birlikte `16#0101` gorulmustur.

SBUS yeniden baglandiginda ayni ESP session altinda frame counter tekrar
ilerlemis; uc saglikli snapshot sonrasinda `DataValid=TRUE`,
`FrameCounterFresh=TRUE` ve `RejectBits=0` recovery gerceklesmistir.

Bu regresyon normal ileri sayac ve yerel donma timeout davranisini kanitlar.
G16 counter backward/toggle ve uint32 wrap hata enjeksiyonlari ayri test
kaniti gerektirir.

Sonuç: **PASS**

## SBUS hattı ayrılması

SBUS hattı fiziksel olarak ayrıldı.

Gözlenen sonuç:

- `DataValid = FALSE`
- `FrameCounterFresh = FALSE`
- `HealthySnapshotCount = 0`
- `RejectBits = 16#0101`

`RejectBits` yorumu:

- `16#0100`: SBUS frame counter freshness timeout
- `16#0001`: kabul edilmiş snapshot watchdog timeout

Typed validated DB son kabul edilmiş payload değerlerini korudu ancak
`DB_ValidatedG16Input.Data.Valid` değerini `FALSE` yaptı. Bu beklenen
fail-silent davranıştır; payload yalnız `Valid=TRUE` iken kullanılabilir.

Sonuç: **PASS**

## SBUS hattının yeniden bağlanması

Gözlenen sonuç:

1. `FrameCounterFresh` tekrar `TRUE` oldu.
2. `HealthySnapshotCount` yeniden kuruldu.
3. Üç sağlıklı snapshot sonrasında `DataValid=TRUE` oldu.
4. `RejectBits=16#0000` oldu.

Sonuç: **PASS**

## Kalan testler

- SBUS receiver tarafından gönderilen gerçek lost/failsafe frame'leri

## ESP cold-boot, session ve neutral re-arm

ESP enerjisi fiziksel olarak kesilip yeniden verildi.

Session gözlemi:

- restart öncesi `SessionId = 16#EEAA_17B6`
- restart sonrası `SessionId = 16#24DB_EE86`
- restart sonrası sequence düşük değerden yeniden başladı
- restart sonrası gateway monotonic zaman düşük değerden yeniden başladı

Güç kesintisinde authority önce controlled-stop davranışına girdi, ardından:

- `State = 0`
- `ActiveAuthority = 0`
- `ManualAuthorityGranted = FALSE`
- `MotionInhibit = TRUE`
- `LastTransitionReason = 16#0003`

Recovery sırasında joystick non-neutral tutulduğunda:

- `State = 2`
- `ActiveAuthority = 0`
- `ManualAuthorityGranted = FALSE`
- `MotionInhibit = TRUE`
- `WaitingForNeutral = TRUE`

Joystick neutral konuma döndürüldükten ve neutral-hold koşulu tamamlandıktan
sonra:

- `State = 3`
- `ActiveAuthority = 1`
- `ManualAuthorityGranted = TRUE`
- `MotionInhibit = FALSE`
- `WaitingForNeutral = FALSE`

Sonuç: **PASS**

## Kumandanın güç düğmesinden kapatılması ve açılması

ESP ve Ethernet bağlantısı çalışırken G16 kumandası kendi güç düğmesinden
kapatıldı.

Kumanda açıkken:

- `DataValid = TRUE`
- `FrameCounterFresh = TRUE`
- `RejectBits = 16#0000`
- `HealthySnapshotCount = 3`
- `State = 3`
- `ManualAuthorityGranted = TRUE`
- `MotionInhibit = FALSE`

Kumanda kapatıldığında:

- `DataValid = FALSE`
- `FrameCounterFresh = FALSE`
- `RejectBits = 16#0101`
- `HealthySnapshotCount = 0`
- `State = 0`
- `ActiveAuthority = 0`
- `ManualAuthorityGranted = FALSE`
- `MotionInhibit = TRUE`
- `LastTransitionReason = 16#0003`

Son kabul edilmiş typed snapshot içinde `SbusFlags = 16#0009`,
`ChannelValidMask = 16#FFFF`, `FrameLostCount = 0` ve `FailsafeCount = 0`
değerleri korundu. Bu alanlar `Valid=FALSE` iken kontrol verisi değildir.
Receiver, kumanda kapandıktan sonra lost/failsafe bitlerini taşıyan yeni bir
SBUS frame üretmediği için sayaçların artmaması beklenen davranıştır.

Kumanda yeniden açıldığında:

- ESP session değişmedi: `SessionId = 16#38B1_C1FF`
- SBUS frame counter yeniden ilerledi
- `DataValid = TRUE`
- `FrameCounterFresh = TRUE`
- `RejectBits = 16#0000`
- `HealthySnapshotCount = 3`
- `State = 3`
- `ManualAuthorityGranted = TRUE`
- `MotionInhibit = FALSE`

Sonuç: **PASS**

## Ethernet bağlantısının ayrılması ve yeniden bağlanması

ESP çalışmaya devam ederken PLC–ESP Ethernet bağlantısı fiziksel olarak
ayrıldı.

Bağlantı öncesi:

- `DataValid = TRUE`
- `FrameCounterFresh = TRUE`
- `RejectBits = 16#0000`
- `HealthySnapshotCount = 3`
- `State = 3`
- `ActiveAuthority = 1`
- `ManualAuthorityGranted = TRUE`

Ethernet ayrıldığında:

- `DataValid = FALSE`
- `FrameCounterFresh = FALSE`
- `RejectBits = 16#0101`
- `HealthySnapshotCount = 0`
- `State = 0`
- `ActiveAuthority = 0`
- `ManualAuthorityGranted = FALSE`
- `MotionInhibit = TRUE`
- `LastTransitionReason = 16#0003`

Ethernet yeniden bağlandığında:

- ESP session değişmedi: `SessionId = 16#38B1_C1FF`
- `DataValid = TRUE`
- `FrameCounterFresh = TRUE`
- `RejectBits = 16#0000`
- `HealthySnapshotCount = 3`
- `State = 3`
- `ActiveAuthority = 1`
- `ManualAuthorityGranted = TRUE`
- `MotionInhibit = FALSE`

Bağlantı dönüşünde sequence ilerledi ve aynı ESP session altında veri akışı
yeniden kuruldu. `MB_CLIENT.Error` darbe şeklinde olabileceğinden ekran
görüntüsünde yakalanmadı; validator timeout ve authority geçişleri bağlantı
kaybını deterministik olarak doğruladı.

Sonuç: **PASS**

# PTO Servo Axis Commissioning

Bu belge küçük test aracındaki iki pulse/direction servo için ön ayarları
tanımlar. Değerler fiziksel limit ve gerilim ölçümleri tamamlanmadan production
ayarları değildir.

## Ortak donanım

- CPU: S7-1200 CPU 1214C DC/DC/DC, firmware V4.6
- Servo arayüzü: pulse/direction
- Servo elektronik gearing: `10000 pulse / motor revolution`
- Axis tipi: Positioning axis / PTO
- Axis engineering unit: degree
- Servo alarm: her eksen için ayrı PLC dijital girişine alınacak
- Servo enable: test aracında ortak `Q0.3` çıkışıyla kontrollü
- Servo reset: ayrı çıkış kullanılmayacak; gerekli olursa araç dururken ortak
  enable kontrollü biçimde çevrilecek

Siemens CPU 1214C örnek PTO ataması:

| Axis | Pulse | Direction |
|---|---|---|
| PTO1 / Steering | `Q0.0` | `Q0.4` |
| PTO2 / Throttle | `Q0.1` | `Q0.5` |
| PTO3 / Brake | `Q0.2` | `Q0.6` |

Kesin adresler TIA Device configuration içindeki Pulse generators/PTO ekranında
doğrulanmalıdır; aynı çıkışlar normal program çıkışı olarak kullanılmamalıdır.

Doğrulanan Technology Object ve ayrılmış home girişleri:

| Technology Object | Instance DB | Home input |
|---|---:|---|
| `Steering_Axis` | DB11 | `I0.1` |
| `Throttle_Axis` | DB12 | `I0.2` |
| `Brake_Axis` | DB13 | `I0.3` |

Mevcut test aracında `UseAxisHoming = FALSE` olacak ve hiçbir `MC_Home` çağrısı
yapılmayacaktır. Home sensörleri gelecekte kullanım için yalnızca ayrılmıştır.
Brake axis oluşturulmuş fakat `BrakeAxisInstalled = FALSE` olarak power, home ve
hareket komutlarına kapalı rezerv eksendir.

Doğrulanan standart dijital I/O planı:

| Adres | Sinyal |
|---|---|
| `I0.0` | `EStopChainOk` |
| `I0.1` | `SteeringHome` |
| `I0.2` | `ThrottleHome` |
| `I0.3` | `BrakeHome` |
| `I0.4` | `WheelEncoderA` / HSC3 |
| `I0.5` | `WheelEncoderB` / HSC3 |
| `I0.6` | `SteeringServoAlarmOk` |
| `I0.7` | `ThrottleServoAlarmOk` |
| `I1.0` | `BrakeServoAlarmOk` |
| `Q0.3` | `ServoEnable_All` |

Alarm sinyalleri program tarafında pozitif mantığa normalize edilmelidir:
`TRUE = servo healthy`. Kurulu olmayan Brake ekseninin boş alarm girişi genel
izni kesmez. `ServoEnable_All` standart PLC çalışma iznidir; fiziksel E-stop
servo/STO veya sürücü enable zincirini donanımsal olarak da kesmelidir.

## Steering axis

Mekanik:

- Motor kasnağı: `17` diş
- Teker/pot kasnağı: `62` diş
- Motor revolutions / load revolutions: `62 / 17 = 3.6470588235`
- Pulse / load revolution: `10000 × 62 / 17 = 36470.588235`
- Pulse / load degree: `36470.588235 / 360 = 101.3071895`

Technology Object mekanik alanlarında tercih edilen giriş:

```text
Motor revolutions = 62
Load revolutions  = 17
Position per load revolution = 360 degree
Pulse per motor revolution = 10000
```

TIA ekranı oranı ters adlandırıyorsa sonuç mutlaka şu kontrolle doğrulanmalıdır:

```text
360 degree load command = 36470.588 pulse
1 degree load command   = 101.307 pulse
```

Direksiyon gerçek mekanik açı limiti henüz ölçülmedi. Potun yaklaşık 270°
elektriksel/mekanik aralığı, tekerin izin verilen direksiyon açısı olarak kabul
edilmez. Software limitler teker açısı ve pot voltajı birlikte ölçülmeden
açılmamalıdır.

İlk enerjili test için önerilen commissioning dinamikleri:

```text
Maximum velocity     = 5 deg/s
Maximum acceleration = 10 deg/s^2
Maximum deceleration = 10 deg/s^2
Jerk                 = düşük/default
```

İlk test hareketi en fazla `±1 degree` olmalı ve pulse yönü ile pot değişimi
gözlenmelidir.

## Throttle axis

Mekanik:

- Servo ile pot: `1:1`
- Pot maksimum mekanik hareketi: yaklaşık `270 degree`
- Pulse / degree: `10000 / 360 = 27.7777778`
- Teorik 270° hareket: `7500 pulse`

Technology Object mekanik alanları:

```text
Motor revolutions = 1
Load revolutions  = 1
Position per load revolution = 360 degree
Pulse per motor revolution = 10000
```

270° pot fiziksel sınırına komut verilmemelidir. Ölçüm öncesi eksen power
edilmez. Pot uç voltajları ve DC motor sürücüsünün kabul ettiği gerçek aralık
ölçüldükten sonra güvenli minimum/maksimum açı belirlenir; iki uçta mekanik ve
elektriksel margin bırakılır.

İlk enerjili test için önerilen commissioning dinamikleri:

```text
Maximum velocity     = 5 deg/s
Maximum acceleration = 10 deg/s^2
Maximum deceleration = 10 deg/s^2
Jerk                 = düşük/default
```

İlk test hareketi en fazla `1 degree` olmalı. Pot voltajının doğru yönde
değiştiği ve DC motor sürücüsünün beklenmedik hareket üretmediği doğrulanmalıdır.

## Homing / actual position

PTO pulse sayacı mutlak pot konumunu kendiliğinden bilmez. Her PLC/servo yeniden
başlangıcında axis actual position ile fiziksel pot konumu yeniden
eşleştirilmelidir.

Kalıcı çözüm seçenekleri:

1. Dijital reference switch ile standart active homing.
2. Pot kalibrasyonundan hesaplanan fiziksel dereceyi, hareket yasakken direct
   homing/set-position işlemiyle axis actual position'a yüklemek.

İkinci seçenek uygulanacaksa pot sinyali önce range/plausibility kontrolünden
geçmeli; servo disabled, araç durmuş ve hareket inhibit aktif olmalıdır.

## Enerji vermeden önce zorunlu kontroller

- Servo pulse/direction giriş elektrik seviyesi ve PLC sourcing çıkış uyumu
- Pulse ve direction polaritesi
- Servo enable/alarm/reset wiring ve aktif seviyeleri
- Pot besleme, minimum, maksimum ve nötr voltajları
- PLC analog input ortak referansı
- DC motor sürücüsü pot girişinin gerçekten `0..5 V` olup olmadığı
- PLC AI ile DC sürücü girişinin paralel bağlanmasının üretici tarafından uygunluğu
- Direksiyon mekanik sağ/sol limitleri
- Gaz potu mekanik marginleri
- Fiziksel E-stop ile servo enable ve DC drive inhibit davranışı

Pot sinyali DC sürücüye doğrudan hız referansı veriyorsa yanlış servo hareketi
motoru anında sürebilir. Throttle axis commissioning sırasında DC motor sürücü
enable/inhibit hattı fiziksel olarak kapalı tutulmalıdır.

## Wheel encoder

Doğrulanan encoder:

```text
Manufacturer: Kübler
Model: 05.2420.121C.1000
Type: incremental A/B quadrature with zero/index
Resolution: 1000 pulse/revolution
Supply: 5..24 VDC, max. 50 mA
```

Üretici kablo renkleri:

| Renk | Sinyal |
|---|---|
| White (WH) | 0 V |
| Brown (BN) | +V supply |
| Green (GN) | Channel A |
| Yellow (YE) | Channel B |
| Grey (GY) | Zero/index, 1 pulse/revolution |

`I0.0` E-stop izleme ve `I0.1..I0.3` gelecekteki home sensörleri için ayrıldığı
için encoder'da HSC1 kullanılmayacaktır. Doğrulanan HSC ataması:

```text
HSC3 mode = A/B quadrature
Channel A = I0.4
Channel B = I0.5
Zero/index = başlangıçta kullanılmayacak ve ayrı izole edilecek
Evaluation = 4-fold, doğrulanacak count = 4000 count/wheel revolution
```

Grey zero/index hattı otomatik HSC reset'e bağlanırsa cumulative distance her
turda sıfırlanır. Bu nedenle ilk hız/odometry uygulamasında kullanılmaz.

Encoder tekerle 1:1 bağlıysa:

```text
wheel_revolutions = count_delta / 4000
wheel_rpm = count_delta / sample_time_s × 60 / 4000
wheel_speed_mps = count_delta / sample_time_s × PI × wheel_diameter_m / 4000
distance_m = cumulative_count × PI × wheel_diameter_m / 4000
```

Gerçek count/revolution değeri teker bir tam tur elle çevrilerek doğrulanmalıdır.
Ters yönde count azalması beklenir; yön tersse A/B kanalları veya yazılım yön
işareti kontrollü biçimde değiştirilir.

Encoder'ın 5..24 V modeli 24 V ile beslenecekse besleme regüle olmalı ve 24 V'u
aşmamalıdır. Encoder 0 V ile PLC M referansı ortaklanmalı, kablo shield'i pano
tarafında uygun PE/shield bar'a alınmalıdır.

## Test aracı program çağrısı

TIA'ya aşağıdaki kaynaklar sırayla import/compile edilir:

1. `UDT_VehicleHardwareStatus.scl`
2. `DB_VehicleHardwareStatus.scl`
3. `FB_VehicleHardwareIO.scl`

FB için TIA'nın oluşturduğu instance DB kullanılır. OB1 çağrısındaki test aracı
konfigürasyonu:

```text
SteeringAxisInstalled = TRUE
ThrottleAxisInstalled = TRUE
BrakeAxisInstalled = FALSE
UseAxisHoming = FALSE
ServoEnableRequest = TRUE
MotionInhibit = DB_AuthorityStatus.Data.MotionInhibit
ServoEnableAll => Q0.3 / ServoEnable_All
```

Fiziksel alarm sinyallerinin aktif seviyesi servo sürücü şemasıyla doğrulanıp FB
girişine `TRUE = healthy` olacak şekilde bağlanır. Brake kurulmadığı sürece
`BrakeServoAlarmOkRaw` girişinin değeri genel servo iznini etkilemez.

`FB_VehicleHardwareIO` authority state machine'den önce çağrılır ve ürettiği
`SafetyChainOk` sinyali authority bloğuna verilir. `MotionInhibit` bir önceki
authority sonucundan geldiği için ortak enable'ın açılması/kapanmasında en fazla
bir OB çevrimi gecikme olabilir; fiziksel E-stop kesmesi bundan bağımsız ve
donanımsaldır.

## Steering supervisor ve MC blokları

Mevcut test aracında steering için `MC_Home` veya `MC_MoveAbsolute`
kullanılmayacaktır. Pot gerçek teker açısını verir; `FB_SteeringAxisSupervisor`
kumanda/Orin isteğini hedef açıya çevirir ve pot hatasına göre `MC_MoveJog`
girişlerini üretir.

Kaynak import sırası:

1. `UDT_SteeringAxisStatus.scl`
2. `DB_SteeringAxisStatus.scl`
3. `FB_SteeringAxisSupervisor.scl`

Supervisor çıkış bağlantıları:

```text
AxisPowerEnable         -> MC_Power.Enable
JogPositive             -> MC_MoveJog.JogForward
JogNegative             -> MC_MoveJog.JogBackward
JogVelocityDegPerSec    -> MC_MoveJog.Velocity
MC_Power.Error OR MC_MoveJog.Error -> AxisMotionError
```

Her iki MC bloğunda Axis girişi `Steering_Axis` teknoloji nesnesine bağlanır.
`MC_Power` önce, `MC_MoveJog` sonra çağrılır. Başlangıç için acceleration ve
deceleration teknoloji nesnesindeki düşük commissioning değerlerinde kalır.

Hareketi açmadan önce ölçülmesi gereken parametreler:

```text
PotRawAtMinAngle    = mekanik güvenli sol limitte IW64
PotRawAtCenter      = teker düzken IW64
PotRawAtMaxAngle    = mekanik güvenli sağ limitte IW64
MinAngleDeg         = ölçülmüş güvenli sol teker açısı
CenterAngleDeg      = 0.0
MaxAngleDeg         = ölçülmüş güvenli sağ teker açısı
```

Supervisor v0.2 başlangıç değerleri:

```text
CommissioningEnable            = FALSE (ölçümler girilene kadar)
PotHardLimitMarginRaw          = 200
StopToleranceDeg               = 0.7
RestartToleranceDeg            = 1.4
VelocityGain                   = 4.0
MinimumJogVelocityDegPerSec    = 1.0
ManualMinimumRateDegPerSec     = 10.0
ManualMaximumRateDegPerSec     = 100.0
AutoRateAtZeroSpeedDegPerSec   = 50.0
AutoRateAtHighSpeedDegPerSec   = 8.0
AutoRateHighSpeedMps           = 6.0
VelocityAccelerationDegPerSec2 = 150.0
VelocityDecelerationDegPerSec2 = 250.0
CycleTimeSec                   = gerçek çağrı periyodu [s]
JogDirectionInvert             = fiziksel testte belirlenecek
```

Manuel modda AUX2 artık açı aralığını küçültmez. Tam joystick her AUX2
konumunda `MinAngleDeg..MaxAngleDeg` aralığını kullanır; AUX2 yalnız tepki/rate
limitini `ManualMinimumRateDegPerSec..ManualMaximumRateDegPerSec` arasında
ayarlar. Auto modda Orin doğrudan `AutoTargetAngleDeg` gönderir ve rate limiti
geçerli `VehicleSpeedMps` üzerinden doğrusal olarak azaltılır.

`DesiredTargetAngleDeg` ham istek, `TargetAngleDeg` ise rate-limit uygulanmış
hedeftir. `StopToleranceDeg` içinde jog durur ve hata
`RestartToleranceDeg` dışına çıkmadan tekrar başlamaz. `PotHardLimitMarginRaw`
çalışma limitindeki küçük overshoot'u tolere eder; hard sınıra doğru hareketi
keserken içeri dönüşe izin verir.

`CycleTimeSec = 0.01` yalnız supervisor ve iki MC bloğu sabit 10 ms çağrılıyorsa
kullanılır. OB1 içinde çağrılıyorsa gerçek/ölçülmüş scan süresi saniye olarak
bağlanmalıdır; yanlış büyük değer yazılım rampasını beklenenden hızlı yapar.
Production düzeninde steering supervisor, `MC_Power` ve `MC_MoveJog` aynı sabit
periyotlu cyclic interrupt OB içinde çalıştırılmalıdır.

İlk enerjili testte araç tekerleri yerden kaldırılmalı, kumanda steering isteği
çok küçük tutulmalı ve yanlış yönde hareket görülürse enable derhal
kapatılmalıdır. `CommissioningEnable` yalnızca pot kalibrasyonu doğrulandıktan
sonra TRUE yapılır.

## Controlled stop doğrulaması

`ControlledStopComplete` sabit TRUE değildir. Production sistemde geçerli teker
hızı eşik altında, throttle güvenli konumda ve fren uygulanmış veya drive torque
fiziksel olarak inhibit edilmiş olmalıdır. Bu koşullar belirli süre kesintisiz
sağlandıktan sonra authority state machine'e tamamlandı bilgisi verilir.

Teker encoder ve throttle kontrolü tamamlanana kadar
`FB_ControlledStopMonitor` bench modunda kullanılabilir. Kaynak import sırası:

1. `UDT_ControlledStopStatus.scl`
2. `DB_ControlledStopStatus.scl`
3. `FB_ControlledStopMonitor.scl`

Mevcut bench bağlantısı:

```text
BenchMode               = TRUE
MotionInhibit           = DB_AuthorityStatus.Data.MotionInhibit
DriveTorqueInhibited    = fiziksel traction inhibit doğrulaması
BrakeApplied            = FALSE
VehicleSpeedValid       = FALSE
VehicleSpeedMps         = 0.0
StopSpeedThresholdMps   = 0.05
ThrottleFeedbackValid   = FALSE
ThrottleActualAngleDeg  = 0.0
ThrottleSafeAngleDeg    = 0.0
ThrottleToleranceDeg    = 1.0
ConfirmationTime        = T#1S
ControlledStopComplete  -> FB_AuthorityStateMachine.ControlledStopComplete
```

`DriveTorqueInhibited` yalnız DC traction motor sürücüsü gerçekten fiziksel
olarak inhibit edilmiş veya enerjisizse TRUE yapılmalıdır. Gerçek sürüş
başladığında `BenchMode = FALSE` yapılır; encoder hızı, throttle pot geri
bildirimi ve brake/drive-inhibit geri bildirimi bağlanmadan production koşulu
complete üretmez.

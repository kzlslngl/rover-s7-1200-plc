# Authority State Machine Bench Acceptance — 2026-08-14

## Test ortamı

- CPU: Siemens S7-1200 CPU 1214C DC/DC/DC
- Sipariş numarası: `6ES7 214-1AG40-0XB0`
- CPU firmware: V4.6
- TIA Portal: V20
- PLC bench IP: `192.168.2.100/24`
- ESP gateway IP: `192.168.2.166/24`
- G16 Modbus TCP snapshot validator: geçerli

Testler watch table ve geçici BOOL girişleriyle gerçekleştirilmiştir. Fiziksel
aktüatör çıkışı sürülmemiştir.

## Sonuçlar

| Test | Beklenen | Sonuç |
|---|---|---|
| MANUAL neutral re-arm | 500 ms nötr sonrası `MANUAL_ACTIVE` | PASS |
| MANUAL sırasında layout değişimi | controlled stop ve motion inhibit | PASS |
| MANUAL sırasında G16 kaybı | grace olmadan controlled stop | PASS |
| AUTO girişinde Orin geçerliliği | Orin valid değilken `AUTO_WAIT_ORIN` | PASS |
| AUTO sırasında Orin kaybı | controlled stop, sonra Orin bekleme | PASS |
| AUTO sırasında kısa G16 kaybı | 2 s grace içinde AUTO korunur | PASS |
| AUTO sırasında uzun G16 kaybı | grace sonunda controlled stop | PASS |
| Safety chain kaybı | `FAULT`, authority yok, motion inhibit | PASS |
| Fault reset kapısı | safety OK + durmuş + G16 valid + MOD kapalı | PASS |

## Doğrulanan sınırlar

- `ManualAuthorityGranted` yalnız geçerli G16 ve neutral re-arm sonrasında TRUE.
- `AutoAuthorityGranted` yalnız geçerli Orin adayı varken TRUE.
- MANUAL kaynağı kaybolduğunda son joystick komutu tutulmuyor.
- AUTO sırasında G16 kaybı yalnız yapılandırılmış grace süresince tolere ediliyor.
- Orin kaybına G16 grace uygulanmıyor.
- Kaynak veya kontrol layout'u değişikliği doğrudan yetki aktarımı yapmıyor.
- Bütün non-active durumlarda `MotionInhibit=TRUE`.

## Production öncesi açık maddeler

- `SafetyChainOk`, gerçek salt-okunur safety/interlock aynasına bağlanmalı.
- `ControlledStopComplete`, ölçülen araç hızı ve aktüatör feedback'i ile üretilmeli.
- `OrinValid`, ana protokol sözleşmesine göre yazılacak snapshot validator'dan gelmeli.
- Grace ve neutral süreleri HIL ölçümü/risk değerlendirmesiyle kesinleştirilmeli.
- Bu test safety-rated E-stop/STO zincirinin doğrulaması değildir.

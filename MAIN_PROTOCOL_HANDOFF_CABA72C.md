# Ana Protokol `caba72c` PLC Uygulama Handoff'u

Son güncelleme: 20 Ağustos 2026

Bu belge PLC Codex'inin ana rover projesinde tamamlanan Modbus TCP v1.1
sözleşmesini TIA/SCL uygulamasına aktarması için doğrudan uygulama girdisidir.
TIA/SCL kodu içermez ve wire sözleşmesinin bağımsız otoritesi değildir.

Ana kaynak:

- depo: [kzlslngl/rover-core-ros2](https://github.com/kzlslngl/rover-core-ros2);
- dal: `agent/local-metric-map`;
- commit: `caba72c7cce4fdc64328caa1b586c3be68077b23`;
- şema: `rover_hardware/config/plc_protocol_v1.yaml`;
- vektörler: `rover_hardware/config/plc_protocol_v1_test_vectors.yaml`;
- sözleşme: `docs/PLC_ORIN_G16_HABERLESME_SOZLESMESI.md`.

Çelişkide ana commit'teki YAML otoritedir. Bu depoda offset, bit, enum,
endian, CRC, session, freshness veya authority anlamı değiştirilmez.

## 1. Bu handoff ile kapanan önceki açıklar

Aşağıdaki alanlar artık TBD değildir:

- `g16_summary_flags`;
- `fault_bits`;
- `interlock_bits`;
- `PLC_DIAGNOSTICS` payload'ı;
- `ACTIVE_CONFIG` payload'ı;
- command dışındaki beş tam 64-register bilinen-sonuç vektörü;
- reserved-zero ve tam protocol-minor eşleşmesi.

PLC Codex'i eski “diagnostics/config payload sıfır kalsın” geçici davranışını
uygulamaz. Ancak validity koşulu sağlanmayan bir alanı sırf tanımlandı diye
geçerli yayınlamaz.

## 2. Değişmeyen snapshot kuralları

Her blok 64 holding register'dır:

```text
magic, major=1, minor=1, length=64
begin_sequence
payload ve reserved-zero
crc32
end_sequence = begin_sequence
```

Zorunlu kurallar:

1. Orin command offset `0`, quantity `64` tek FC16 ile gelir.
2. PLC output blokları ayrı offsetlerde quantity `64` FC03 ile okunur.
3. CRC-32/ISO-HDLC, ilk 60 register'ın high-byte-first byte akışındadır.
4. Protocol major ve minor tam `1.1` eşleşmelidir.
5. Belgelenmiş bütün reserved register'lar sıfır olmalıdır.
6. Raw DB'den doğrudan safety, authority veya actuator hesabı yapılmaz.
7. PLC output alanı her scan typed modelden yeniden encode edilir.

## 3. Kesin bit alanları

### 3.1 `g16_summary_flags` — state offset 106

| Bit | Maske | Ad |
|---:|---:|---|
| 0 | `16#0001` | `FRAME_VALID` |
| 1 | `16#0002` | `FRAME_LOST` |
| 2 | `16#0004` | `RECEIVER_FAILSAFE` |
| 3 | `16#0008` | `DECODER_ALIVE` |
| 4 | `16#0010` | `DECODER_FAULT` |
| 5 | `16#0020` | `CHANNEL_CALIBRATION_VALID` |
| 6 | `16#0040` | `MANUAL_READY` |

Bit `7..15` sıfırdır. `MANUAL_READY` yalnız G16 frame/heartbeat freshness,
kalibrasyon, gerekli channel mask, neutral handshake ve PLC interlock
koşulları birlikte geçerliyse açılır.

### 3.2 `fault_bits` — state offset 80..81, `DWord`

| Bit | Ad | Bit | Ad |
|---:|---|---:|---|
| 0 | `PLC_INTERNAL_FAULT` | 6 | `BRAKE_FAULT` |
| 1 | `CONFIGURATION_FAULT` | 7 | `SPEED_FEEDBACK_FAULT` |
| 2 | `ORIN_COMMAND_LINK_FAULT` | 8 | `CONTACTOR_FEEDBACK_FAULT` |
| 3 | `G16_GATEWAY_FAULT` | 9 | `CONTROLLED_STOP_FAULT` |
| 4 | `DRIVE_FAULT` | 10 | `SAFETY_CHAIN_FAULT` |
| 5 | `STEERING_FAULT` | 11 | `WATCHDOG_FAULT` |

Bit `12..31` sıfırdır. Bitin latched/active davranışı PLC tasarımında açıkça
belgelenir; bu alan safety reset komutu değildir.

### 3.3 `interlock_bits` — state offset 82..83, `DWord`

| Bit | Ad | Bit | Ad |
|---:|---|---:|---|
| 0 | `ESTOP_ACTIVE` | 8 | `MANUAL_G16_INVALID` |
| 1 | `SAFETY_RELAY_NOT_HEALTHY` | 9 | `LOCALIZATION_INVALID` |
| 2 | `DRIVE_NOT_READY` | 10 | `NAVIGATION_UNHEALTHY` |
| 3 | `CONTACTOR_NOT_CONFIRMED` | 11 | `GEOFENCE_INVALID` |
| 4 | `BRAKE_NOT_READY` | 12 | `MISSION_TIME_INVALID` |
| 5 | `STEERING_NOT_READY` | 13 | `MANUAL_NEUTRAL_REQUIRED` |
| 6 | `ACTIVE_CONFIG_INVALID` | 14 | `CONTROLLED_STOP_ACTIVE` |
| 7 | `AUTO_COMMAND_INVALID` | 15 | `AUTHORITY_REARM_REQUIRED` |

Bit `16..31` sıfırdır. Interlock biti o anda izin vermeyen nedeni gösterir;
fault latch ile aynı kavram değildir.

## 4. `PLC_DIAGNOSTICS` — offset 192..255

Header `192..197`, footer `252..255`, reserved `242..251` sıfırdır.

| Offset | TIA tipi | Typed alan |
|---:|---|---|
| 198–199 | `DWord` | `PlcSessionId` |
| 200–201 | `DWord` | `DiagnosticHeartbeat` |
| 202–203 | `DWord` | `PlcMonotonicMs` |
| 204–205 | `DWord` | `ScanTimeUs` |
| 206–207 | `DWord` | `MaxScanTimeUs` |
| 208 | `Word` | `DiagnosticFlags` |
| 209 | `Word` | `MbServerStatus` |
| 210 | `Word` | `EspMbClientStatus` |
| 211 | `UInt` | `LastCommandRejectReason` |
| 212–213 | `DWord` | `OrinCommandAcceptCount` |
| 214–215 | `DWord` | `OrinCommandRejectCount` |
| 216–217 | `DWord` | `OrinCrcErrorCount` |
| 218–219 | `DWord` | `OrinProtocolErrorCount` |
| 220–221 | `DWord` | `OrinTimeoutCount` |
| 222–223 | `DWord` | `EspPollSuccessCount` |
| 224–225 | `DWord` | `EspPollErrorCount` |
| 226–227 | `DWord` | `EspCrcErrorCount` |
| 228–229 | `DWord` | `EspStaleCount` |
| 230–231 | `DWord` | `G16InvalidFrameCount` |
| 232–233 | `DWord` | `G16FrameLostCount` |
| 234–235 | `DWord` | `G16FailsafeCount` |
| 236–237 | `DWord` | `ControlledStopCount` |
| 238–239 | `DWord` | `FaultTransitionCount` |
| 240–241 | `DWord` | `OutputWriteViolationCount` |

`DiagnosticFlags`:

| Bit | Ad | Bit | Ad |
|---:|---|---:|---|
| 0 | `SCAN_TIME_VALID` | 5 | `G16_FRAME_FRESH` |
| 1 | `ORIN_SERVER_RUNNING` | 6 | `SAFETY_INPUTS_VALID` |
| 2 | `ESP_CLIENT_CONNECTED` | 7 | `ACTUATOR_FEEDBACK_VALID` |
| 3 | `ORIN_COMMAND_FRESH` | 8 | `COUNTERS_VALID` |
| 4 | `ESP_SNAPSHOT_FRESH` | 9 | `OUTPUT_WRITE_VIOLATION` |

Bit `10..15` sıfırdır. Connected/running bitleri freshness veya hareket
izni değildir. Sayaçlar `DWord` wrap eder.

## 5. `ACTIVE_CONFIG` — offset 256..319

Header `256..261`, footer `316..319`, reserved `303..315` sıfırdır.

| Offset | TIA tipi | Typed alan | Not |
|---:|---|---|---|
| 262–263 | `DWord` | `ConfigVersion` | Sıfır geçersiz olabilir |
| 264–265 | `DWord` | `ConfigCrc32` | Canonical config CRC |
| 266 | `Word` | `ConfigFlags` | Aşağıda |
| 267 | `UInt` | `G16LossPolicy` | Aşağıda |
| 268–269 | `DWord` | `CommandTimeoutMs` | ms |
| 270–271 | `DWord` | `OrinHeartbeatTimeoutMs` | ms |
| 272–273 | `DWord` | `G16FrameTimeoutMs` | ms |
| 274–275 | `DWord` | `G16GatewayTimeoutMs` | ms |
| 276–277 | `DWord` | `ControlledStopTimeoutMs` | ms |
| 278–279 | `DWord` | `ManualNeutralHoldMs` | ms |
| 280–281 | `DWord` | `AutoG16GraceMs` | Kullanılmıyorsa sıfır |
| 282–283 | `Real` | `MaxForwardSpeedMps` | Pozitif büyüklük |
| 284–285 | `Real` | `MaxReverseSpeedMps` | Pozitif büyüklük |
| 286–287 | `Real` | `MaxSteeringAngleRad` | Pozitif büyüklük |
| 288–289 | `Real` | `MaxAccelerationMps2` | Pozitif büyüklük |
| 290–291 | `Real` | `MaxDecelerationMps2` | Pozitif büyüklük |
| 292–293 | `Real` | `MaxSteeringRateRadps` | Pozitif büyüklük |
| 294–295 | `Real` | `ControlledStopDecelerationMps2` | Pozitif büyüklük |
| 296–297 | `Real` | `WheelbaseM` | Pozitif |
| 298–299 | `DWord` | `G16CalibrationVersion` | - |
| 300–301 | `DWord` | `G16CalibrationCrc32` | - |
| 302 | `UInt` | `BrakeEffectUnit` | Aşağıda |

`ConfigFlags` bitleri:

| Bit | Ad | Bit | Ad |
|---:|---|---:|---|
| 0 | `CONFIGURED` | 5 | `G16_CALIBRATION_VALID` |
| 1 | `COMMAND_TIMEOUT_VALID` | 6 | `VEHICLE_GEOMETRY_VALID` |
| 2 | `G16_TIMEOUTS_VALID` | 7 | `FEEDBACK_UNITS_VALID` |
| 3 | `MOTION_LIMITS_VALID` | 8 | `G16_LOSS_POLICY_VALID` |
| 4 | `CONTROLLED_STOP_PROFILE_VALID` | - | - |

Bit `9..15` sıfırdır. Gerekli validity bitlerinden biri kapalıysa PLC AUTO'ya
izin vermez ve `ACTIVE_CONFIG_INVALID` interlock'unu yayınlar.

`G16LossPolicy` enum'u:

| Değer | Ad | Kullanım |
|---:|---|---|
| 0 | `STOP_ALL_MODES` | İlk bench ve entegrasyon varsayılanı |
| 1 | `AUTO_GRACE_THEN_STOP` | Risk analizi/HIL sonrası |
| 2 | `AUTONOMOUS_CONTINUE_GUARDED` | Risk analizi/HIL sonrası |

`BrakeEffectUnit`: `0 UNCONFIGURED`, `1 PERCENT`, `2 KILOPASCAL`, `3 NEWTON`,
`4 DECELERATION_MPS2`.

## 6. PLC session ve restart sözleşmesi

Her CPU boot'unda yeni, sıfırdan farklı `PlcSessionId` üretilir. Önerilen
kaynak retentive boot counter'dır; wrap sonucu sıfır oluşursa bir sonraki
sıfır-olmayan değer kullanılır. Cihaz kimliğiyle karıştırma kullanılacaksa
algoritma export ve commissioning belgesinde sabitlenir.

Şunlar non-retentive kalır ve boot'ta safe-disabled olur:

- raw command;
- accepted command/session cache'i;
- authority ve state-machine geçiş durumu;
- actuator target'ları;
- freshness zamanları ve validity cache'i.

PLC restart sonrası Orin cache invalid eder; PLC kendiliğinden önceki AUTO veya
MANUAL authority'yi geri yüklemez.

## 7. G16 frame-counter freshness zorunluluğu

`sbus_frame_counter` yalnız yeni kullanılabilir SBUS frame ile ilerler. Her
FC03 poll'unda değişmesi beklenmez. PLC validator şu state'i ayrı tutar:

- son görülen frame counter;
- son farklı counter'ın görüldüğü PLC-local monotonic zaman;
- configured `G16FrameTimeoutMs`;
- `FrameCounterFresh` sonucu.

Counter configured pencere içinde ilerlemezse G16 invalid olur; gateway
heartbeat ilerliyor veya TCP connected olsa bile MANUAL kullanılamaz.
ESP session değişimi counter state'ini sıfırlar ve neutral/re-arm gerektirir.

## 8. Ortak bilinen-sonuç test kapısı

Ana YAML'daki bütün 64 register listeleri PLC watch table/test FB ile birebir
karşılaştırılır. Hızlı CRC kontrol tablosu:

| Vektör | Sequence | Beklenen CRC32 |
|---|---:|---:|
| `command_snapshot` | `42` | `16#5C224D43` |
| `plc_state_snapshot` | `16#01020304` | `16#F25E58F7` |
| `g16_status_snapshot` | `16#00000020` | `16#1FD9B9B1` |
| `plc_diagnostics_snapshot` | `16#00000030` | `16#02530C29` |
| `active_config_snapshot` | `16#00000040` | `16#4B764F17` |
| `esp_snapshot` | `16#01020304` | `16#12749618` |

CRC eşleşip register listesi farklıysa test başarısızdır. Wrong minor,
non-zero reserved, bad CRC ve begin/end mismatch ayrı negatif testlerdir.

## 9. PLC Codex'i için uygulanacak sıra

1. Bu dalı uygulama dalına kontrollü al; belge çakışmalarını ana commit'e göre
   çöz.
2. Önce `FB_G16SnapshotValidator` frame-counter freshness eksikliğini kapat.
3. Kumanda kapanması, SBUS kesilmesi, ESP reseti ve Ethernet kopması testlerini
   fiziksel çıkışsız kaydet.
4. `DB_ModbusServerRaw[0..319]`, command staging ve typed validator katmanını
   kur; raw DB non-optimized/non-retentive olsun.
5. `PlcSessionId` boot üretimini ekle.
6. PLC state, G16, diagnostics ve active-config typed publisher'larını kur.
7. Dört output encoder'ını ortak tam vektörlerle doğrula.
8. Output write-violation detection ve aynı-scan republish testini yap.
9. VM ile önce salt-okunur FC03 bench testini tamamla.
10. Aktüatör enerjisiz/ayrılmışken yalnız `SAFE_DISABLED` ve
    `CONTROLLED_STOP` FC16 kabul/reject testini yap.
11. Authority ve gerçek actuator adaptörü bundan sonra bağlanır.

## 10. VM–PLC bench kabul kapısı

İlk VM testi hareket testi değildir. Gerekli koşullar:

- TIA sürümü, CPU sipariş/firmware bilgisi kaydedilmiş;
- PLC `MB_SERVER` çalışıyor ve raw DB non-optimized/non-retentive;
- PLC ve VM aynı bench subnet'inde;
- aktüatör çıkışları fiziksel olarak enerjisiz veya ayrılmış;
- E-stop/safety zinciri gerçek durumuyla izleniyor, bypass yok;
- tek Modbus command writer VM'dir.

Test sırası:

1. ICMP erişimi ve TCP port `502`;
2. FC03 offset `64`, `128`, `192`, `256`, her biri quantity `64`;
3. magic, `1.1`, length, equal sequence, CRC ve reserved-zero;
4. PLC session/heartbeat progression;
5. PLC restart sonrası yeni session ve safe-disabled;
6. yalnız kontrollü-stop command snapshot'ı ile FC16 offset `0`, quantity
   `64`;
7. accepted session/sequence veya deterministik reject reason geri bildirimi;
8. duplicate, bad CRC, wrong minor ve non-zero reserved negatif enjeksiyonu.

Bu testler geçmeden VM'den hız/direksiyon hedefi veya drive-enable talebi
gönderilmez.

## 11. Ana Proje Codex'i notu

Bu belgeyi hazırlayan Ana Proje Codex'i, `rover-core-ros2` sistem uyumluluğu
ve güvenlik sözleşmesi denetçisidir. TIA/SCL uygulamasını yazmaz, PLC'ye
download yapmaz ve safety onayı vermez. İstenen alanların kaynağı ana rover
projesindeki `caba72c` protokol commit'idir. PLC Codex'i uygulama, compile,
export, PLCSIM/CPU ve HIL kanıtlarının sahibidir.

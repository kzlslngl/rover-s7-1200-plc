# Orin–PLC DB ve Tag Sözleşmesi

Son inceleme: 20 Ağustos 2026

Bu belge S7-1200 PLC ile Jetson Orin üzerindeki ROS 2 adapteri arasında
kullanılacak sembolik DB/UDT ve tag yapısını sabitler. TIA/SCL kodu içermez.
Wire alanlarının otoritesi:

- `rover-core-ros2/rover_hardware/config/plc_protocol_v1.yaml`;
- `rover-core-ros2/rover_hardware/config/plc_protocol_v1_test_vectors.yaml`;
- `rover-core-ros2/docs/PLC_ORIN_G16_HABERLESME_SOZLESMESI.md`.

Wire protokolü `1.1`'dir. Bu belge yeni offset, bit veya enum tanımlamaz.

## Belge sahibi ve Codex rolleri

Bu belgeyi hazırlayan **Ana Proje Codex'i**yim. Ana çalışma ve sistem
otoritesi kaynağım
[kzlslngl/rover-core-ros2](https://github.com/kzlslngl/rover-core-ros2)
projesidir. Buradaki görevim PLC uygulamasını yazmak değil, ayrı geliştirilen
ROS 2, PLC ve ESP bileşenlerinin aynı wire, güvenlik ve authority
sözleşmesini kullanmasını denetlemektir.

Ana Proje Codex'i:

- TIA/SCL, PLC DB/UDT veya fiziksel I/O uygulaması yazmaz ve değiştirmez;
- TIA compile, PLCSIM veya cihaza download çalıştırmaz;
- ana ROS şemasını, PLC exportlarını ve Git diff'lerini salt-okunur inceler;
- uyumsuzlukları, eksik kararları ve kabul kriterlerini yalnız Markdown
  belgeleriyle bildirir.

PC'de bu depoyla çalışan **PLC Codex'i** uygulama sahibidir. PLC Codex'i:

- bu belge, `DECISIONS.md` ve `PLC_INTEGRATION_GUIDE.md` dosyalarını zorunlu
  giriş sözleşmesi olarak okur;
- TIA/SCL, UDT, DB, tag ve test uygulamasını oluşturabilir;
- compile, PLCSIM ve kullanıcı onayıyla gerçek CPU test kanıtı üretebilir;
- wire offset, endian, CRC, enum, bit, session, freshness veya authority
  anlamlarını bağımsız değiştiremez;
- bir çelişki bulursa tahmin yürütmez; Ana Proje Codex'ine ve
  `rover-core-ros2` ana sözleşmesine upstream bulgu olarak iletir.

Bu belge otomatik kod veya güvenlik onayı değildir. Uygulama ancak ilgili
commit, TIA compile, test vektörü, PLCSIM/CPU ve gerekli HIL kanıtları
incelendikten sonra kabul edilir.

## 1. Şimdi belirlenebilecek ve beklemesi gereken kararlar

DB/tag tasarımına başlamak için erken değildir. Aşağıdakiler artık sabittir:

- PLC, Modbus TCP server ve nihai hareket otoritesidir;
- Orin tek yetkili command writer'dır;
- PLC server alanı `ARRAY[0..319] OF WORD` biçiminde beş adet 64-register
  blok taşır;
- command yazımı tek FC16, blok okumaları tam FC03 isteğidir;
- raw transport, validated typed model ve actuator/safety katmanları ayrıdır;
- snapshot, CRC, session, heartbeat, sequence, freshness ve range doğrulamaları
  hareket hesabından önce yapılır;
- program mantığı fiziksel DB numarası yerine sembolik ad kullanır.

Aşağıdakiler henüz sabitlenmez:

- fiziksel DB numaraları;
- PLC/Orin production IP, VLAN, ACL ve connection ID;
- gerçek I/Q adresleri ve terminal isimleri;
- motor, fren, direksiyon ve encoder donanım tag'leri;
- production heartbeat/command timeout ve hareket limitleri;
- gerçek G16 kanal kalibrasyon değerleri ve fren geri bildirim birimi;
- production `g16_loss_policy` seçimi; ilk bench değeri
  `STOP_ALL_MODES` olmalıdır.

TBD değerler sıfırla temsil edilmez. Ayrı `Configured` ve `Valid` alanları
kullanılır.

## 2. Wire ve DB sınırı

PLC'nin Orin'e sunduğu tek MB_SERVER raw alanı:

| Raw index | Wire offset | Blok | Sahip | Orin işlemi |
|---:|---:|---|---|---|
| `0..63` | `0x0000..0x003F` | `ORIN_TO_PLC_COMMAND` | Orin | tek FC16 write |
| `64..127` | `0x0040..0x007F` | `PLC_TO_ORIN_STATE` | PLC | tam FC03 read |
| `128..191` | `0x0080..0x00BF` | `G16_STATUS` | PLC | tam FC03 read |
| `192..255` | `0x00C0..0x00FF` | `PLC_DIAGNOSTICS` | PLC | tam FC03 read |
| `256..319` | `0x0100..0x013F` | `ACTIVE_CONFIG` | PLC | tam FC03 read |

ESP'nin `320..383` alanı PLC MB_SERVER DB'sinin devamı değildir. Ayrı
ESP server'ından PLC `MB_CLIENT` ile okunan ayrı 64-WORD buffer'dır.

Siemens `40001` gösterimi ana sözleşmede wire adresi değildir. Orin
adapteri sıfır tabanlı offset kullanır. TIA'daki Modbus instruction adres
gösterimi ayrıca commissioning kanıtıyla kaydedilir.

## 3. Zorunlu raw ve instance DB'leri

| Sembolik DB | Önerilen içerik | Optimized | Retentive | Kontrol kaynağı |
|---|---|---|---|---|
| `DB_ModbusServerRaw` | `Holding[0..319] : ARRAY OF WORD` | hayır | hayır | hayır |
| `DB_OrinCommandStagingRaw` | `Registers[0..63]` | olabilir | hayır | hayır |
| `DB_ExpectedPublishedRaw` | `Registers[64..319]` | olabilir | hayır | hayır |
| `DB_EspGatewayRxRaw` | `Registers[0..63]` | Siemens blok şartına göre | hayır | hayır |
| `DB_MbServerInstance` | `MB_SERVER` instance | TIA tarafından | hayır | hayır |
| `DB_EspMbClientInstance` | `MB_CLIENT` instance | TIA tarafından | hayır | hayır |
| `DB_OrinConnection` | server/connection config | olabilir | deployment kararı | hayır |
| `DB_EspConnection` | ESP client connection config | olabilir | deployment kararı | hayır |

`DB_ModbusServerRaw` global, non-optimized ve non-retentive olmalıdır.
Boot'ta sıfırlanır. Raw command, validity cache'i, authority ve actuator
hedefi hiçbir durumda retentive olmaz.

`DB_ModbusServerRaw[0..63]` MB_SERVER çağrısından sonra staging buffer'a
kopyalanır. Bir validation çevrimi boyunca raw DB tekrar okunmaz. Begin/end
sequence ile CRC, FC16 sırasında oluşabilecek torn görüntüyü reddeder.

Standart `MB_SERVER` PLC output bölgesine dış yazmayı fiziksel olarak
engellemeyebilir. PLC:

1. output bloklarını typed publisher DB'lerinden üretir;
2. `DB_ExpectedPublishedRaw` ile beklenen görüntüyü tutar;
3. `64..319` alanındaki beklenmeyen dış değişimi diagnostic ihlal sayar;
4. aynı scan sonunda PLC-owned output alanını yeniden yayımlar;
5. raw output alanını safety veya actuator hesabında hiçbir zaman okumaz.

## 4. Typed çalışma DB'leri

| Sembolik DB | Tip/model | Görev |
|---|---|---|
| `DB_ValidatedOrinCommand` | `UDT_OrinCommandValidated` | yalnız tamamen kabul edilmiş Orin komutu |
| `DB_OrinCommandValidation` | `UDT_CommandValidationStatus` | reject, age, sequence ve session tanıları |
| `DB_ValidatedG16Input` | `UDT_G16ValidatedInput` | ESP snapshot validator çıktısı |
| `DB_G16Calibration` | `UDT_G16Calibration` | mapping/min/nötr/max/deadband/yön/sürüm |
| `DB_ControlState` | `UDT_ControlState` | operational state ve authority |
| `DB_PlcStatePublisher` | `UDT_PlcStateModel` | `PLC_TO_ORIN_STATE` typed staging |
| `DB_G16StatusPublisher` | `UDT_G16StatusModel` | `G16_STATUS` typed staging |
| `DB_Diagnostics` | `UDT_PlcDiagnosticsLocal` | yerel sayaçlar; wire payload'dan bağımsız |
| `DB_ActiveConfig` | `UDT_ActiveConfigLocal` | gerçekten uygulanan PLC config |
| `DB_SafetyInputs` | `UDT_SafetyInputMirror` | salt-okunur fiziksel safety/interlock aynası |
| `DB_ActuatorTargets` | `UDT_ActuatorTargets` | guard sonrası hedefler, non-retentive |
| `DB_ActuatorFeedback` | `UDT_ActuatorFeedback` | ölçülen değerler ve validity |

Typed DB'ler optimized olabilir. Wire encode/decode yalnız ayrılmış
fonksiyon/FB katmanında yapılır. Typed model raw register dizilimini taklit
etmek zorunda değildir.

Retentive olabilecek sınırlı veriler:

- PLC boot/session counter;
- onaylı config version/CRC;
- lifetime diagnostic sayaçları.

Retentive veriden boot sonrası authority veya hareket hedefi geri yüklenmez.

## 5. Orin command typed tag'leri

`UDT_OrinCommandValidated` en az aşağıdaki alanları içerir:

| Typed tag | Kaynak offset | TIA tipi | Kullanım |
|---|---:|---|---|
| `Valid` | yerel | `Bool` | tüm kabul zincirinin sonucu |
| `SessionId` | 6–7 | `DWord` | Orin process kimliği |
| `HeartbeatCounter` | 8–9 | `DWord` | link canlılık sayacı |
| `CommandSequence` | 10–11 | `DWord` | yeni command sayacı |
| `OrinMonotonicMs` | 12–13 | `DWord` | Orin clock-domain tanısı |
| `RequestedMode` | 14 | `UInt` | protokol enum'u |
| `CommandFlags` | 15 | `Word` | protokol bitfield'i |
| `TargetSpeedMps` | 16–17 | `Real` | işaretli araç hızı |
| `TargetSteeringAngleRad` | 18–19 | `Real` | REP-103 merkez direksiyon açısı |
| `AccelerationLimitMps2` | 20–21 | `Real` | pozitif limit |
| `DecelerationLimitMps2` | 22–23 | `Real` | pozitif limit |
| `SteeringRateLimitRadps` | 24–25 | `Real` | pozitif limit |
| `MissionSpeedLimitMps` | 26–27 | `Real` | görev üst sınırı |
| `CommandValidityMs` | 28–29 | `DWord` | PLC üst sınırını aşamaz |
| `AcceptedAtPlcTime` | yerel | PLC monotonic tip | age hesabının başlangıcı |

`CommandFlags` için typed convenience Bool alanları üretilebilir, ancak wire
`Word` tek otoritedir:

- `CommandValid`;
- `AutonomousRequest`;
- `ControlledStopRequest`;
- `LocalizationValid`;
- `NavigationHealthy`;
- `GeofenceValid`;
- `MissionTimeValid`.

Bu Bool'lar decode sonucudur; ayrı bağımsız tag olarak force edilip wire
anlamını değiştiremez.

## 6. Command validation tag'leri

`UDT_CommandValidationStatus` için önerilen sembolik alanlar:

| Tag | Tip | Anlam |
|---|---|---|
| `SnapshotValid` | `Bool` | header/begin-end/CRC sonucu |
| `DataValid` | `Bool` | bütün validation ve freshness sonucu |
| `RejectReason` | `UInt` | ana `command_reject_reason` enum'u |
| `CalculatedCrc` / `WireCrc` | `DWord` | tanı |
| `LastSeenSessionId` | `DWord` | son görülen session |
| `AcceptedSessionId` | `DWord` | son kabul edilmiş session |
| `LastHeartbeat` | `DWord` | son heartbeat değeri |
| `LastCommandSequence` | `DWord` | son command değeri |
| `HeartbeatAgeMs` | `DWord` | PLC yerel ölçümü |
| `CommandAgeMs` | `DWord` | PLC yerel ölçümü |
| `SessionRearmRequired` | `Bool` | yeni Orin session kapısı |
| `TransportError` / `TransportStatus` | `Bool` / `Word` | MB_SERVER tanısı |

Orin ve PLC monotonic saatleri birbirinden çıkarılmaz. Age değerleri son
ilerlemeyi PLC'nin gördüğü yerel monotonic zamandan hesaplanır.

İlk başarısız kontrol deterministik `RejectReason` olur:

1. header, length, begin/end, reserved;
2. protocol version;
3. CRC;
4. session/re-arm;
5. heartbeat progression/age;
6. command sequence progression/age;
7. command validity;
8. finite ve range;
9. safety/fault/interlock/manual override;
10. autonomy/localization/navigation/geofence/mission guard'ları.

## 7. PLC state publisher tag'leri

`UDT_PlcStateModel`, wire offset `64..127` için en az şu alanları taşır:

| Typed tag | Wire offset | Tip |
|---|---:|---|
| `PlcSessionId` | 70–71 | `DWord` |
| `HeartbeatCounter` | 72–73 | `DWord` |
| `PlcMonotonicMs` | 74–75 | `DWord` |
| `OperationalState` | 76 | `UInt` |
| `ActiveAuthority` | 77 | `UInt` |
| `StatusFlags` | 78 | `Word` |
| `CommandRejectReason` | 79 | `UInt` |
| `FaultBits` | 80–81 | `DWord` |
| `InterlockBits` | 82–83 | `DWord` |
| `AcceptedOrinSessionId` | 84–85 | `DWord` |
| `AcceptedCommandSequence` | 86–87 | `DWord` |
| `CommandAgeMs` | 88–89 | `DWord` |
| `OrinHeartbeatAgeMs` | 90–91 | `DWord` |
| `ActualSpeedMps` | 92–93 | `Real` |
| `ActualSteeringAngleRad` | 94–95 | `Real` |
| `ThrottlePositionPercent` | 96–97 | `Real` |
| `BrakePositionPercent` | 98–99 | `Real` |
| `BrakeEffectValue` | 100–101 | `Real` |
| `LeftWheelSpeedMps` | 102–103 | `Real` |
| `RightWheelSpeedMps` | 104–105 | `Real` |
| `G16SummaryFlags` | 106 | `Word` |
| `SafetySummaryFlags` | 107 | `Word` |
| `G16FrameAgeMs` | 108–109 | `DWord` |
| `G16FrameCounter` | 110–111 | `DWord` |

`FaultBits`, `InterlockBits` ve `G16SummaryFlags` bit anlamları ana proje
commit `caba72c` ile kesinleşmiştir. PLC yalnız
`MAIN_PROTOCOL_HANDOFF_CABA72C.md` içindeki tanımlı bitleri yayınlar; rezerve
bitler sıfırdır ve wire'a özel yeni bit uydurulmaz.

Her ölçüm yalnız ilgili `StatusFlags` validity bitiyle anlamlıdır. Geçersiz
ölçümün sayısal değeri safety veya hareket kararı değildir.

## 8. G16 ve config publisher sınırı

`DB_G16StatusPublisher`, kabul edilmiş ESP verisini ve PLC kalibrasyon
sonucunu Orin'e sunar. PLC'nin manuel kontrol kaynağı bu publish DB veya raw
Modbus alanı değil, `DB_ValidatedG16Input` ile `DB_G16Calibration` olur.

G16 validity için birlikte zorunludur:

- gateway session biliniyor;
- gateway heartbeat configured pencerede ilerliyor;
- SBUS frame counter configured pencerede ilerliyor;
- gateway frame age ve PLC local counter-age limit içinde;
- valid/alive açık, lost/failsafe/fault kapalı;
- gerekli channel mask bitleri açık;
- kalibrasyon sürümü geçerli.

`PLC_DIAGNOSTICS` ve `ACTIVE_CONFIG` payload offsetleri ana proje commit
`caba72c` ile kesinleşmiştir. Typed publisher DB'leri
`MAIN_PROTOCOL_HANDOFF_CABA72C.md` tablolarına göre encode edilir. Validity
bitleri gerçek yerel doğrulama sonucudur; yalnız alan mevcut diye açılmaz.
Tanımlı payload dışında kalan reserved register'lar sıfırdır.

## 9. Tag isimlendirme standardı

Sembolik adlar İngilizce ASCII ve birimli olmalıdır:

| Prefix | Kapsam | Örnek |
|---|---|---|
| `Raw_` | wire register/staging | `Raw_OrinCommand` |
| `Net_` | transport/connection | `Net_OrinClientConnected` |
| `Cmd_` | validated command | `Cmd_TargetSpeedMps` |
| `State_` | operational/authority | `State_ActiveAuthority` |
| `G16_` | receiver/manual input | `G16_FrameCounterAgeMs` |
| `Safe_` | safety mirror/guard | `Safe_EstopActive` |
| `Act_` | actuator target/feedback | `Act_SteeringFeedbackRad` |
| `Diag_` | reject/fault counter | `Diag_OrinCrcRejectCount` |
| `Cfg_` | validated config | `Cfg_CommandTimeoutMs` |

Birim suffix'leri atlanmaz: `Mps`, `Rad`, `Mps2`, `Radps`, `Ms`,
`Percent`. Wire offset veya fiziksel DB numarası tag adına gömülmez.

Global PLC tag tablosuna yalnız fiziksel I/O, system constant ve commissioning
bağlantıları konur. Program içi veri sembolik UDT/DB alanıdır.

Önerilen fiziksel tag aileleri şimdiden adlandırılabilir fakat adreslenmez:

- `DI_Safety_*`, `DI_Interlock_*`, `DI_Feedback_*`;
- `DO_Drive_*`, `DO_Brake_*`, `DO_Steering_*`;
- `AI_*`, `AO_*`, `HSC_*`;
- `HW_ProfinetInterface`.

Gerçek terminal ve elektrik şeması kesinleşmeden `%I`, `%Q`, `%IW`,
`%QW` adresi atanmaz.

## 10. PLC scan veri akışı

Her scan için sahiplik sırası:

1. fiziksel safety/interlock/feedback girişlerini aynala;
2. `MB_SERVER` ve ESP `MB_CLIENT` communication instruction'larını çağır;
3. Orin command raw bloğunu staging'e kopyala;
4. Orin ve ESP snapshot'larını doğrula;
5. yalnız kabul edilmiş veriyi typed working DB'lere atomik aktar;
6. local freshness/restart/config guard'larını hesapla;
7. authority state machine'i çalıştır;
8. controlled-stop veya normal rate/trajectory limitlerini uygula;
9. safety/interlock guard'larından sonra actuator target üret;
10. feedback/state/diagnostics/config typed publish modellerini oluştur;
11. dört PLC output snapshot'ını encode et, CRC/sequence ekle;
12. beklenen görüntüyü ve raw server output alanını aynı scan'de güncelle.

`DONE`, `CONNECTED` veya TCP socket varlığı hareket izni değildir.

## 11. Orin adapter sorumlulukları

Orin tarafı:

- command bloğunu typed modelden tam 64 register staging görüntüsüne encode
  eder;
- reserved alanları sıfırlar;
- begin sequence dahil ilk 60 register üzerinden CRC hesaplar;
- CRC ve aynı end sequence değerini yazar;
- tek FC16 isteğiyle offset `0`, quantity `64` gönderir;
- PLC output bloklarını ayrı tam FC03 okumalarıyla alır ve doğrular;
- PLC session değişiminde state cache'ini invalid eder;
- Modbus yazma başarısını hareket kabulü saymaz; accepted session/sequence ve
  PLC state geri bildirimini bekler.

İlk ROS adapteri `plc_command_adapter_node` olabilir; node/package adı wire
sözleşmesinin parçası değildir. Web UI PLC register'larına doğrudan erişmez.

## 12. Uygulama ve kabul sırası

PLC Codex'i için ilk güvenli sıra:

1. bu belgeyi, `DECISIONS.md`, `MAIN_PROTOCOL_HANDOFF_CABA72C.md` ve ana YAML
   ile birlikte uygulama dalına al;
2. sembolik UDT/DB'leri fiziksel çıkış bağlantısı olmadan oluştur;
3. raw MB_SERVER DB'nin non-optimized/non-retentive kanıtını kaydet;
4. endian, CRC ve command known-result `0x5C224D43` vektörünü doğrula;
5. command validator'ı watch/diagnostics-only çalıştır;
6. duplicate, torn, bad CRC, wrong version, session ve timeout testlerini yap;
7. PLC state, G16, diagnostics ve active-config encoder'larını beş ortak tam
   snapshot vektörüyle karşılaştır;
8. VM'den salt-okunur FC03 ile dört PLC output bloğunu doğrula;
9. ancak bundan sonra authority ve actuator adaptörüne typed bağlantı kur.

Her TIA exportunda fiziksel DB numarası–sembolik ad tablosu, optimized ve
retentive özellikler, compile sonucu ve test kanıtı kaydedilir.

Bu sözleşme tamamlanmış actuator tasarımı değildir. Orin–PLC haberleşme
iskeletini donanımdan bağımsız ve güvenli biçimde kurmak için yeterli
başlangıç otoritesidir.

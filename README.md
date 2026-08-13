# Rover S7-1200 PLC

Siemens S7-1200 tabanlı rover kontrolü, Modbus TCP haberleşmesi, G16 manuel
yetki yolu, kontrollü duruş ve PLC güvenlik interlock uygulaması.

Hedef PLC:

- Siemens S7-1200 CPU 1214C DC/DC/DC
- TIA Portal sürümü: henüz kesinleşmedi
- PLC firmware ve genişleme modülleri: henüz kesinleşmedi
- Haberleşme sözleşmesi: Modbus TCP protokolü v1.1

Bu depo TIA Portal projesini, metin olarak dışa aktarılmış PLC kaynaklarını,
DB/UDT tanımlarını, protokol kopyasını ve kabul testlerini ROS 2 ile ESP32
firmware depolarından bağımsız sürümlemek içindir.

## Sözleşme kaynakları

Protokolün ana otoritesi `rover_core_ros2` deposundadır:

- Referans commit: `66f6bde8b457ff8ef04ed045184f519dc34e5ef2`
- İnsan-okunur sözleşme:
  `docs/PLC_ORIN_G16_HABERLESME_SOZLESMESI.md`
- Makine-okunur register şeması:
  `rover_hardware/config/plc_protocol_v1.yaml`
- Ortak bilinen-sonuç testleri:
  `rover_hardware/config/plc_protocol_v1_test_vectors.yaml`
- ESP elektriksel profili:
  `rover_hardware/config/g16_gateway.yaml`

G16 gateway firmware:
[kzlslngl/rover-g16-gateway-firmware](https://github.com/kzlslngl/rover-g16-gateway-firmware)

## PLC Codex başlangıç sırası

PC'de bu depo için açılacak PLC geliştirme görevi işe şu sırayla başlamalıdır:

1. [`DECISIONS.md`](DECISIONS.md): sistem güvenliği, wire sözleşmesi ve PLC
   mimari sınırları;
2. [`PLC_INTEGRATION_GUIDE.md`](PLC_INTEGRATION_GUIDE.md): ESP gateway
   bağlantısı, tam register haritası, CRC vektörü ve HIL kabul adımları;
3. TIA Portal sürümü, CPU firmware'i ve gerçek ağ profilini kaydetme;
4. fiziksel çıkış üretmeden UDT/DB, endian/CRC yardımcıları ve snapshot
   validator geliştirme.

Bu depodaki **PLC Codex'i** TIA/SCL uygulamasını yazan ve PC üzerinde
derleme/test kanıtı üreten taraftır. Belgelerde kendisini tanıtan **Ana Proje
Codex'i** ise `rover-core-ros2` kaynaklı sistem sözleşmesini denetleyen,
yalnız Markdown bulgusu yazan ayrı roldür.

> Offset, endian, CRC, alan anlamı veya güvenlik semantiği bu depoda bağımsız
> değiştirilmez. Önce ana protokol sözleşmesi sürümlenir, ardından PLC ve
> firmware depolarına taşınır.

## Değişmeyecek güvenlik sınırları

1. PLC nihai hareket otoritesi ve komut kaynağı seçiminin sahibidir.
2. Orin yalnız fiziksel anlamı açık hız, direksiyon, ivme/yavaşlama ve
   controlled-stop hedefleri gönderir.
3. Orin doğrudan gaz, fren, motor pulse veya safety çıkışı sürmez.
4. G16 manuel kontrol yolu Orin kapalıyken de PLC'ye ulaşır.
5. Modbus protokolü safety-rated değildir.
6. E-stop, safety relay/F-CPU, drive STO ve kontaktör zinciri Modbus'tan
   bağımsızdır.
7. E-stop reset, safety bypass ve STO bypass Modbus register'larında bulunmaz.
8. Ham Modbus buffer hiçbir zaman doğrudan kontrol veya aktüatör hesabında
   kullanılmaz.
9. Limit dışı değer sessizce clamp edilmez; komut açık bir nedenle reddedilir.
10. Ağ bağlantısının açık olması freshness veya hareket izni değildir.

## Haberleşme topolojisi

```text
Orin
  |
  | Modbus TCP, tek yetkili command client
  | FC16 command write / FC03 state read
  v
S7-1200 MB_SERVER
  |
  +--> snapshot doğrulama
  +--> authority ve controlled-stop state machine
  +--> safety/interlock kontrolleri
  +--> araç kontrol/aktüatör adaptörleri

S7-1200 MB_CLIENT
  |
  | ayrı Modbus TCP bağlantısı, yalnız FC03
  v
ESP32-ETH01 MB_SERVER
  |
  v
GR01/G16 ham SBUS kanalları
```

- Başlangıç Modbus Unit ID: `1`
- TCP port: `502`, yalnız kontrol ağında
- Orin, PLC ve ESP için statik IP planı henüz kesinleşmedi
- Web UI veya tablet PLC register'larına doğrudan erişmez

## Protokol register alanı

Adresler sıfır tabanlı holding-register offset'idir. `40001` gösterimi
sözleşmede kullanılmaz.

| Offset | Boyut | Sahip | Erişim | Blok |
|---|---:|---|---|---|
| `0x0000-0x003F` | 64 | Orin | read/write | `ORIN_TO_PLC_COMMAND` |
| `0x0040-0x007F` | 64 | PLC | read-only | `PLC_TO_ORIN_STATE` |
| `0x0080-0x00BF` | 64 | PLC/G16 | read-only | `G16_STATUS` |
| `0x00C0-0x00FF` | 64 | PLC | read-only | `PLC_DIAGNOSTICS` |
| `0x0100-0x013F` | 64 | PLC | read-only | `ACTIVE_CONFIG` |
| `0x0140-0x017F` | 64 | ESP | PLC poll/read-only | `ESP_TO_PLC_G16_INPUT` |
| `0x0180-0x01FF` | 128 | rezerve | erişim yok | gelecek sürüm |

İlk beş blok PLC'nin Orin'e sunduğu server alanıdır: toplam 320 register.
`ESP_TO_PLC_G16_INPUT` ise ESP'nin kendi server'ında offset 320'de bulunur;
PLC bunu ayrı `MB_CLIENT` bağlantısıyla yerel 64-WORD receive buffer'a okur.

Kodlama:

- register: 16-bit big-endian;
- çok-register alan: high word, ardından low word;
- float: IEEE-754 binary32;
- CRC: CRC-32/ISO-HDLC;
- CRC byte akışı: her register için önce high byte, sonra low byte;
- kontrol vektörü: `"123456789" -> 0xCBF43926`.

Her kritik 64-register blok şu snapshot kalıbını kullanır:

```text
magic + protocol major/minor + block length
begin_sequence
payload + reserved zeros
crc32
end_sequence
```

Snapshot yalnız header ve protokol doğru, begin/end sequence eşit, sequence
yeni, CRC doğru, session/freshness geçerli ve alanlar kabul aralığındaysa
yerel çalışma DB'sine alınır.

## Önerilen TIA DB ve UDT yapısı

Fiziksel DB numaraları bilinçli olarak atanmadı. Sembolik adlar ilk
tasarım hedefidir.

### Ham transport DB'leri

| Sembolik ad | İçerik | Tasarım kuralı |
|---|---|---|
| `DB_ModbusServerHolding` | `ARRAY[0..319] OF WORD` | Orin için ham MB_SERVER alanı |
| `DB_EspGatewayRx` | `ARRAY[0..63] OF WORD` | ESP FC03 sonucunun ham buffer'ı |
| `DB_MbServerInstance` | MB_SERVER instance | yalnız haberleşme durumu |
| `DB_EspMbClientInstance` | MB_CLIENT instance | yalnız ESP poll durumu |

Ham buffer'larda standart/non-optimized erişim gereksinimi kullanılan TIA
sürümü ve Siemens Modbus blok arayüzüyle doğrulanacaktır. Bu karar
doğrulanmadan fiziksel DB numarası sabitlenmez.

### Typed çalışma DB'leri

| Sembolik ad | Görev |
|---|---|
| `DB_ValidatedOrinCommand` | CRC/session/freshness kontrollerinden geçmiş komut |
| `DB_ValidatedG16Input` | doğrulanmış ham kanal snapshot'ı ve kalibrasyon sonucu |
| `DB_ControlState` | operational state, authority ve geçiş zamanlayıcıları |
| `DB_PlcStatePublisher` | Orin'e yayımlanacak PLC state staging alanı |
| `DB_Diagnostics` | hata, reject, scan ve haberleşme sayaçları |
| `DB_ActiveConfig` | gerçekten uygulanan limitler, timeout ve config kimliği |
| `DB_SafetyInputs` | salt-okunur safety/interlock giriş aynası |
| `DB_ActuatorState` | komutlanan/ölçülen aktüatör durumu ve validity |

Önerilen UDT'ler:

- `UDT_OrinCommand`
- `UDT_PlcState`
- `UDT_G16RawInput`
- `UDT_G16CalibratedInput`
- `UDT_ActiveConfig`
- `UDT_Diagnostics`
- `UDT_SafetySummary`
- `UDT_CommandValidationResult`

Typed DB'ler ham wire layout'u taklit etmek zorunda değildir. Wire
encode/decode tek bir katmanda yapılmalı, uygulama mantığı typed alanlarla
çalışmalıdır.

## Önerilen program blokları

| Blok | Sorumluluk |
|---|---|
| `FB_ModbusServer` | Orin MB_SERVER çevrimi ve transport diagnostics |
| `FB_OrinSnapshotValidator` | header, CRC, sequence, session, age ve range doğrulama |
| `FB_EspGatewayClient` | ESP'ye FC03 poll ve reconnect yönetimi |
| `FB_G16SnapshotValidator` | ESP snapshot, counter, age ve failsafe doğrulama |
| `FB_G16Calibration` | sürümlü kanal mapping, endpoint, deadband ve neutral |
| `FB_AuthorityStateMachine` | SAFE/MANUAL/AUTO/STOP/FAULT yetki geçişleri |
| `FB_ControlledStop` | sınırlandırılmış ve izlenen kontrollü duruş profili |
| `FB_SafetyInterlocks` | safety girişlerini salt-okunur guard olarak uygular |
| `FB_StatePublisher` | state/diagnostics/config snapshot'larını atomik yayımlar |
| `FB_ActuatorAdapter` | daha sonra seçilecek drive/servo/I/O adaptörü |

Saf yardımcı fonksiyonlar:

- `FC_Crc32IsoHdlc`
- `FC_ReadU32BigEndian`
- `FC_ReadRealBigEndian`
- `FC_WriteU32BigEndian`
- `FC_WriteRealBigEndian`
- modulo-`2^32` sequence karşılaştırması
- finite/range doğrulama

## Önerilen PLC scan sırası

1. Fiziksel safety, interlock ve feedback girişlerini örnekle.
2. MB_SERVER ve ESP MB_CLIENT haberleşme bloklarını çalıştır.
3. Orin ve ESP ham snapshot'larını staging alanında doğrula.
4. Geçerli snapshot'ları typed çalışma DB'lerine atomik kopyala.
5. Freshness, restart/session ve timeout guard'larını hesapla.
6. Authority state machine'i çalıştır.
7. Controlled-stop ve normal rate/trajectory limitlerini uygula.
8. Safety/interlock guard'larından sonra aktüatör hedefini üret.
9. Feedback, diagnostics, active config ve state snapshot'larını oluştur.
10. PLC'ye ait Modbus output bloklarını atomik biçimde yayımla.

## İlk geliştirme aşaması

İlk değişiklik gerçek çıkış veya hareket üretmemelidir.

1. Kullanılacak TIA Portal sürümünü ve CPU firmware'ini kaydet.
2. Boş CPU 1214C projesini oluştur.
3. Ham transport DB'lerini fiziksel çıkışlara bağlamadan tanımla.
4. Protokol enum/bitfield sabitlerini ve typed UDT'leri oluştur.
5. CRC-32/ISO-HDLC ve endian yardımcılarını SCL olarak yaz.
6. Ortak test vektörlerini PLC watch table veya test FB ile doğrula.
7. Orin command snapshot validator'ı yaz; sonucu yalnız diagnostics/watch
   alanında göster.
8. Duplicate, torn, bad CRC, wrong version, NaN/Inf ve out-of-range
   enjeksiyonlarını test et.

Bu aşama bitmeden authority state machine, MB_CLIENT donanım bağlantısı veya
aktüatör çıkışı eklenmemelidir.

## Açık kararlar

- TIA Portal sürümü
- CPU firmware sürümü ve kesin sipariş kodu
- Fiziksel DB numaraları
- Ham Modbus DB'lerinin optimized/non-optimized yerleşimi
- PLC, Orin ve ESP IP/subnet/VLAN planı
- Heartbeat, command ve G16 timeout değerleri
- G16 kanal mapping ve neutral kalibrasyonu
- Drive/servo/step protokolü ve I/O
- Encoder ve diğer feedback sensörlerinin tipi/ölçeği
- Fren safe-state ve controlled-stop rampası
- Safety relay/E-stop/STO/kontaktör elektriksel mimarisi

Bu kararlar protokol v1.1 offsetlerini ve sahiplik kurallarını değiştirmez.
Gerçek aktüatör testinden önce kritik açık kararlar kapatılmalıdır.

## Önerilen depo yapısı

```text
rover-s7-1200-plc/
├── README.md
├── tia/
│   └── RoverPLC/
├── exported/
│   ├── blocks/
│   ├── db/
│   ├── udt/
│   └── tags/
├── docs/
│   ├── DB_LAYOUT.md
│   ├── STATE_MACHINE.md
│   └── COMMISSIONING.md
├── protocol/
│   ├── plc_protocol_v1.yaml
│   └── plc_protocol_v1_test_vectors.yaml
└── test/
    └── acceptance/
```

TIA Portal projesiyle birlikte mümkün olan her blok, DB, UDT ve tag tablosu
metin/XML/SCL olarak `exported/` altında tutulmalıdır. Böylece binary proje
arşivine ek olarak Git diff ve code review yapılabilir.

Her TIA değişikliğinde:

1. project save/compile;
2. ilgili kaynakların yeniden export edilmesi;
3. compile uyarı ve hatalarının kaydedilmesi;
4. değişen testlerin çalıştırılması;
5. güvenlik etkisinin commit/PR açıklamasında belirtilmesi

beklenir.

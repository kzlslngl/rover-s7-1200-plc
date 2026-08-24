# G16_STATUS Fiziksel FC03 Kabulü — 24 Ağustos 2026

Bu belge Ana Proje Codex'i tarafından, fiziksel PLC/ESP/G16 zincirindeki
`G16_STATUS` publisher uygulamasının salt-okunur Modbus TCP kabul kanıtı
olarak hazırlanmıştır.

Ana proje codec/sözleşme otoritesi:

`rover-core-ros2/agent/local-metric-map@854fee6f67ad3cb37f526c84fbcf79cdcacf10fa`

## Kapsam ve yöntem

| Alan | Değer |
|---|---|
| PLC | `192.168.2.100:502` |
| Modbus unit ID | `1` |
| Fiziksel durum | PLC, ESP ve G16 açık |
| İşlem | Yalnız FC03 |
| Başlangıç | `128 (0x0080)` |
| Uzunluk | `64` register |
| Blok tipi | `G16_STATUS` / `g16_status` |
| Protokol | `1.1` |
| Beklenen magic/type | `0x5247` |
| Codec | Ana ROS `rover_hardware.plc_protocol` |

Tek `ModbusTcpClient` nesnesiyle bir TCP bağlantısı açıldı. Aynı kalıcı
session üzerinden 300 ms aralıklı üç FC03 okuması yapıldı ve bağlantı test
sonunda kapatıldı. PLC'ye FC16 veya başka bir yazma isteği gönderilmedi. PLC,
ESP ve G16 yazılımları değiştirilmedi.

Ana ROS codec'i bloğu `g16_status` şema tipiyle decode etti. `decode_block()`
header, begin/end, global reserved `178..187` (blok-local `50..59`) ve CRC
kontrollerinden geçti. Progression ayrıca `is_newer_sequence()`
modulo-`2^32` karşılaştırmasıyla kontrol edildi.

## Zorunlu kabul kontrolleri

| Kontrol | Örnek 1 | Örnek 2 | Örnek 3 | Karar |
|---|---:|---:|---:|---|
| Magic/blok tipi | `0x5247` | `0x5247` | `0x5247` | Geçti |
| Protocol major/minor | `1/1` | `1/1` | `1/1` | Geçti |
| Block length | `64` | `64` | `64` | Geçti |
| Begin = end | `879` | `889` | `899` | Geçti |
| Sequence ileri | Başlangıç | `+10` | `+10` | Geçti |
| Decoder session sabit/nonzero | `0xC9E7C77E` | Aynı | Aynı | Geçti |
| Decoder heartbeat | `9814` | `9827` | `9839` | Geçti |
| SBUS frame counter | `27506` | `27542` | `27573` | Geçti |
| Frame age | `0 ms` | `0 ms` | `0 ms` | Geçti |
| Hesaplanan CRC = wire CRC | `0x57F90073` | `0x1044A985` | `0x7F185F99` | Geçti |
| Local reserved `50..59` | Tümü `0` | Tümü `0` | Tümü `0` | Geçti |

Decoder heartbeat iki aralıkta `+13`, `+12`; SBUS frame counter `+36`, `+31`
ilerledi. Snapshot publisher, ESP decoder ve gerçek SBUS frame kaynağının
birbirinden bağımsız ama canlı sayaçları fiziksel olarak gözlendi.

## Validity ve kanal semantiği

Üç örnekte de aşağıdaki değerler sabit kaldı:

| Alan | Değer | Yorum |
|---|---:|---|
| `sbus_flags` | `0x0009` | `FRAME_VALID + DECODER_ALIVE` |
| `channel_count` | `16` | Şemadaki üst sınırla uyumlu |
| `channel_valid_mask` | `0xFFFF` | On altı ham kanal mevcut |
| `link_quality` | `0` | Validity biti kapalı; tüketilmez |
| `rssi_dbm` | `0` | Validity biti kapalı; tüketilmez |

`sbus_flags=0x0009` bit ayrıştırması:

| Bit | Ad | Durum |
|---:|---|---|
| 0 | `FRAME_VALID` | Açık |
| 1 | `FRAME_LOST` | Kapalı |
| 2 | `RECEIVER_FAILSAFE` | Kapalı |
| 3 | `DECODER_ALIVE` | Açık |
| 4 | `DECODER_FAULT` | Kapalı |
| 5 | `CHANNEL_CALIBRATION_VALID` | Kapalı |
| 6 | `LINK_QUALITY_VALID` | Kapalı |
| 7 | `RSSI_VALID` | Kapalı |
| 8..15 | Reserved | Kapalı |

Bu desen canlı ve geçerli ham SBUS frame'i doğrular; ancak kalibrasyon geçerli
değildir. Bu nedenle `channel_normalized`, link quality ve RSSI değerleri
üretim kontrolünde kullanılamaz. `channel_valid_mask=0xFFFF`, ham kanalların
snapshot'ta mevcut olduğunu gösterir; calibration validity yerine geçmez.

Ham kanal değerleri üç örnekte de:

```text
[1002, 1002, 1002, 1002, 1002, 1722, 282, 282,
 426, 1722, 1722, 1722, 1002, 1002, 1002, 1002]
```

Normalized kanal dizisi üç örnekte de on altı adet `0` taşıdı. Kalibrasyon
validity biti kapalı olduğundan bu sıfırlar nötr veya geçerli komut olarak
yorumlanmamalıdır. Bu kabul, G16 manual-ready veya kanal kalibrasyonu kabulü
değildir.

## Ham 64-register kanıtı

Aşağıdaki diziler blok-local register `0..63` sırasındadır; her satır sekiz
register içerir.

### Örnek 1

```text
00..07: 5247 0001 0001 0040 0000 036F C9E7 C77E
08..15: 0000 2656 0000 6B72 0000 0009 0010 FFFF
16..23: 03EA 03EA 03EA 03EA 03EA 06BA 011A 011A
24..31: 01AA 06BA 06BA 06BA 03EA 03EA 03EA 03EA
32..39: 0000 0000 0000 0000 0000 0000 0000 0000
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 57F9 0073 0000 036F
```

### Örnek 2

```text
00..07: 5247 0001 0001 0040 0000 0379 C9E7 C77E
08..15: 0000 2663 0000 6B96 0000 0009 0010 FFFF
16..23: 03EA 03EA 03EA 03EA 03EA 06BA 011A 011A
24..31: 01AA 06BA 06BA 06BA 03EA 03EA 03EA 03EA
32..39: 0000 0000 0000 0000 0000 0000 0000 0000
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 1044 A985 0000 0379
```

### Örnek 3

```text
00..07: 5247 0001 0001 0040 0000 0383 C9E7 C77E
08..15: 0000 266F 0000 6BB5 0000 0009 0010 FFFF
16..23: 03EA 03EA 03EA 03EA 03EA 06BA 011A 011A
24..31: 01AA 06BA 06BA 06BA 03EA 03EA 03EA 03EA
32..39: 0000 0000 0000 0000 0000 0000 0000 0000
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 7F18 5F99 0000 0383
```

Local `50..59` alanı her üç ham görüntüde sıfırdır. Local `60..61` CRC ve
`62..63` end sequence alanıdır.

## Nihai kabul

Fiziksel `G16_STATUS` publisher:

- doğru magic/type, protokol, length, begin/end, CRC ve reserved alanları;
- test boyunca sabit/nonzero decoder session;
- ilerleyen publisher sequence, decoder heartbeat ve SBUS frame counter;
- sıfır frame age, geçerli frame ve canlı decoder;
- on altı ham kanal ve açık validity mask

üretti. `G16_STATUS` FC03 publisher fiziksel salt-okunur kabul testini
geçmiştir.

Kalibrasyon, link-quality ve RSSI validity bitleri kapalıdır. Bu nedenle bu
test kanal kalibrasyonu, manual-ready, manual authority veya normalized kanal
değerlerinin üretim kabulü değildir.

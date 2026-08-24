# ACTIVE_CONFIG Fiziksel FC03 Kabulü — 24 Ağustos 2026

Bu belge Ana Proje Codex'i tarafından, PLC Codex'inden gelen fiziksel
`ACTIVE_CONFIG` publisher uygulamasının salt-okunur Modbus TCP kabul kanıtı
olarak hazırlanmıştır.

Ana proje codec/sözleşme otoritesi:

`rover-core-ros2/agent/local-metric-map@854fee6f67ad3cb37f526c84fbcf79cdcacf10fa`

## Kapsam ve yöntem

| Alan | Değer |
|---|---|
| PLC | `192.168.2.100:502` |
| Modbus unit ID | `1` |
| İşlem | Yalnız FC03 |
| Başlangıç | `256 (0x0100)` |
| Uzunluk | `64` register |
| Blok tipi | `ACTIVE_CONFIG` |
| Protokol | `1.1` |
| Beklenen magic/type | `0x5246` |
| Codec | Ana ROS `rover_hardware.plc_protocol` |

Tek `ModbusTcpClient` nesnesiyle bir TCP bağlantısı açıldı. Aynı kalıcı
session üzerinden 300 ms aralıklı üç FC03 okuması yapıldı ve bağlantı test
sonunda kapatıldı. PLC'ye FC16 veya başka bir yazma isteği gönderilmedi. PLC
programı ve TIA projesi değiştirilmedi/download edilmedi.

Ana ROS codec'i bloğu `active_config` şema tipiyle decode etti. Böylece bütün
alanların wire tipleri ve register genişlikleri de şemaya göre doğrulandı.
`decode_block()` header, begin/end, reserved alan ve CRC kontrollerinden geçti.
Progression ayrıca `is_newer_sequence()` modulo-`2^32` karşılaştırmasıyla
kontrol edildi.

## Zorunlu kabul kontrolleri

| Kontrol | Örnek 1 | Örnek 2 | Örnek 3 | Karar |
|---|---:|---:|---:|---|
| Magic/blok tipi | `0x5246` | `0x5246` | `0x5246` | Geçti |
| Protocol major/minor | `1/1` | `1/1` | `1/1` | Geçti |
| Block length | `64` | `64` | `64` | Geçti |
| Begin = end | `3622` | `3625` | `3628` | Geçti |
| Sequence ileri | Başlangıç | `3622 -> 3625` | `3625 -> 3628` | Geçti |
| Hesaplanan CRC = wire CRC | `0xAD8E751C` | `0x073EBD10` | `0x61510514` | Geçti |
| Local reserved `47..59` | Tümü `0` | Tümü `0` | Tümü `0` | Geçti |
| `ConfigFlags` | `0x0006` | `0x0006` | `0x0006` | Geçti |
| Zorunlu timeout değerleri | Eşleşti | Eşleşti | Eşleşti | Geçti |

## Timeout ve geçerli alan doğrulaması

| Alan | Beklenen | Üç örnekte okunan | Karar |
|---|---:|---:|---|
| `command_timeout_ms` | `250` | `250` | Geçti |
| `orin_heartbeat_timeout_ms` | `500` | `500` | Geçti |
| `g16_frame_timeout_ms` | `250` | `250` | Geçti |
| `g16_gateway_timeout_ms` | `2000` | `2000` | Geçti |
| `manual_neutral_hold_ms` | `500` | `500` | Geçti |
| `auto_g16_grace_ms` | `2000` | `2000` | Geçti |

## ConfigFlags doğrulaması

Üç örnekte de `config_flags = 0x0006` okundu. Yalnız bit 1 ve bit 2 açıktır.

| Bit | Ad | Beklenen | Okunan | Karar |
|---:|---|---|---|---|
| 0 | `CONFIGURED` | Kapalı | Kapalı | Geçti |
| 1 | `COMMAND_TIMEOUT_VALID` | Açık | Açık | Geçti |
| 2 | `G16_TIMEOUTS_VALID` | Açık | Açık | Geçti |
| 3 | `MOTION_LIMITS_VALID` | Kapalı | Kapalı | Geçti |
| 4 | `CONTROLLED_STOP_PROFILE_VALID` | Kapalı | Kapalı | Geçti |
| 5 | `G16_CALIBRATION_VALID` | Kapalı | Kapalı | Geçti |
| 6 | `VEHICLE_GEOMETRY_VALID` | Kapalı | Kapalı | Geçti |
| 7 | `FEEDBACK_UNITS_VALID` | Kapalı | Kapalı | Geçti |
| 8 | `G16_LOSS_POLICY_VALID` | Kapalı | Kapalı | Geçti |

Bu desen, yalnız haberleşme timeout sözleşmesinin bu aşamada geçerli olduğunu
gösterir. Mekanik, motion limit, controlled-stop profil, G16 calibration,
vehicle geometry, feedback unit ve G16 loss-policy alanları yayımlansa bile
validity bitleri kapalı olduğu için Orin tarafından üretim değeri olarak
kullanılmamalıdır.

## Decode edilmiş typed alanlar

Sequence ve wire CRC dışında üç örnekte bütün typed değerler aynı kaldı.

| Alan | Örnek 1 | Örnek 2 | Örnek 3 |
|---|---:|---:|---:|
| `begin_sequence` | `3622` | `3625` | `3628` |
| `config_version` | `0` | `0` | `0` |
| `config_crc32` | `0x00000000` | `0x00000000` | `0x00000000` |
| `config_flags` | `0x0006` | `0x0006` | `0x0006` |
| `g16_loss_policy` | `0` | `0` | `0` |
| `command_timeout_ms` | `250` | `250` | `250` |
| `orin_heartbeat_timeout_ms` | `500` | `500` | `500` |
| `g16_frame_timeout_ms` | `250` | `250` | `250` |
| `g16_gateway_timeout_ms` | `2000` | `2000` | `2000` |
| `controlled_stop_timeout_ms` | `0` | `0` | `0` |
| `manual_neutral_hold_ms` | `500` | `500` | `500` |
| `auto_g16_grace_ms` | `2000` | `2000` | `2000` |
| `max_forward_speed_mps` | `2.0` | `2.0` | `2.0` |
| `max_reverse_speed_mps` | `1.0` | `1.0` | `1.0` |
| `max_steering_angle_rad` | `0.60000002` | `0.60000002` | `0.60000002` |
| `max_acceleration_mps2` | `2.0` | `2.0` | `2.0` |
| `max_deceleration_mps2` | `3.0` | `3.0` | `3.0` |
| `max_steering_rate_radps` | `1.0` | `1.0` | `1.0` |
| `controlled_stop_deceleration_mps2` | `0.0` | `0.0` | `0.0` |
| `wheelbase_m` | `0.0` | `0.0` | `0.0` |
| `g16_calibration_version` | `0` | `0` | `0` |
| `g16_calibration_crc32` | `0x00000000` | `0x00000000` | `0x00000000` |
| `brake_effect_unit` | `0` | `0` | `0` |
| `crc32` | `0xAD8E751C` | `0x073EBD10` | `0x61510514` |
| `end_sequence` | `3622` | `3625` | `3628` |

`config_version=0`, `config_crc32=0`, `CONFIGURED=0` ve ilgili validity
bitlerinin kapalı olması kısmi commissioning durumuyla tutarlıdır. Tablodaki
mekanik limit adayları bu aşamada kanonik/üretim config değildir.

## Ham 64-register kanıtı

Aşağıdaki diziler blok-local register `0..63` sırasındadır; her satır sekiz
register içerir.

### Örnek 1

```text
00..07: 5246 0001 0001 0040 0000 0E26 0000 0000
08..15: 0000 0000 0006 0000 0000 00FA 0000 01F4
16..23: 0000 00FA 0000 07D0 0000 0000 0000 01F4
24..31: 0000 07D0 4000 0000 3F80 0000 3F19 999A
32..39: 4000 0000 4040 0000 3F80 0000 0000 0000
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 AD8E 751C 0000 0E26
```

### Örnek 2

```text
00..07: 5246 0001 0001 0040 0000 0E29 0000 0000
08..15: 0000 0000 0006 0000 0000 00FA 0000 01F4
16..23: 0000 00FA 0000 07D0 0000 0000 0000 01F4
24..31: 0000 07D0 4000 0000 3F80 0000 3F19 999A
32..39: 4000 0000 4040 0000 3F80 0000 0000 0000
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 073E BD10 0000 0E29
```

### Örnek 3

```text
00..07: 5246 0001 0001 0040 0000 0E2C 0000 0000
08..15: 0000 0000 0006 0000 0000 00FA 0000 01F4
16..23: 0000 00FA 0000 07D0 0000 0000 0000 01F4
24..31: 0000 07D0 4000 0000 3F80 0000 3F19 999A
32..39: 4000 0000 4040 0000 3F80 0000 0000 0000
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 6151 0514 0000 0E2C
```

Local `47..59` alanı her üç ham görüntüde sıfırdır. Local `60..61` CRC ve
`62..63` end sequence alanıdır.

## Nihai kabul

Fiziksel PLC `ACTIVE_CONFIG` publisher, üç örneğin tamamında:

- doğru ACTIVE_CONFIG magic/type, protokol ve uzunluk header'ı;
- eş begin/end ve ileri snapshot sequence;
- doğru CRC-32/ISO-HDLC;
- sıfır reserved `47..59` alanı;
- tam `0x0006` ConfigFlags deseni;
- istenen command, Orin heartbeat, G16 ve operator timeout değerleri;
- mekanik ve diğer kesinleşmemiş alanlar için kapalı validity bitleri

üretti. `ACTIVE_CONFIG` FC03 publisher fiziksel salt-okunur kabul testini
geçmiştir.

Bu kabul yalnız yayınlanan config snapshot'ın protokol bütünlüğünü ve geçerli
timeout alt kümesini kapsar. Mekanik limitlerin, controlled-stop profilinin,
G16 calibration'ın, vehicle geometry'nin, feedback units'in ve loss policy'nin
üretim geçerliliğini onaylamaz.

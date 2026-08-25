# PLC_STATE Fiziksel FC03 Kabulü — 24 Ağustos 2026

Bu belge Ana Proje Codex'i tarafından, fiziksel PLC'deki `PLC_STATE`
publisher uygulamasının salt-okunur Modbus TCP kabul kanıtı olarak
hazırlanmıştır.

Ana proje codec/sözleşme otoritesi:

`rover-core-ros2/agent/local-metric-map@854fee6f67ad3cb37f526c84fbcf79cdcacf10fa`

## Kapsam ve yöntem

| Alan | Değer |
|---|---|
| PLC | `192.168.2.100:502` |
| Modbus unit ID | `1` |
| İşlem | Yalnız FC03 |
| Başlangıç | `64 (0x0040)` |
| Uzunluk | `64` register |
| Blok tipi | `PLC_STATE` / `plc_to_orin_state` |
| Protokol | `1.1` |
| Beklenen magic/type | `0x5253` |
| Codec | Ana ROS `rover_hardware.plc_protocol` |

Tek `ModbusTcpClient` nesnesiyle bir TCP bağlantısı açıldı. Aynı kalıcı
session üzerinden üç FC03 okuması yapıldı ve bağlantı test sonunda kapatıldı.
PLC'ye FC16 veya başka bir yazma isteği gönderilmedi. PLC programı ve TIA
projesi değiştirilmedi/download edilmedi.

Ana ROS codec'i bloğu `plc_to_orin_state` şema tipiyle decode etti.
`decode_block()` header, begin/end, global reserved `112..123` (blok-local
`48..59`) ve CRC kontrollerinden geçti. Progression ayrıca
`is_newer_sequence()` modulo-`2^32` karşılaştırmasıyla kontrol edildi.

## Zorunlu kabul kontrolleri

| Kontrol | Örnek 1 | Örnek 2 | Örnek 3 | Karar |
|---|---:|---:|---:|---|
| Magic/blok tipi | `0x5253` | `0x5253` | `0x5253` | Geçti |
| Protocol major/minor | `1/1` | `1/1` | `1/1` | Geçti |
| Block length | `64` | `64` | `64` | Geçti |
| Begin = end | `97157` | `97167` | `97176` | Geçti |
| Sequence ileri | Başlangıç | `+10` | `+9` | Geçti |
| PLC heartbeat ileri | `97157` | `97167` | `97176` | Geçti |
| PLC monotonic ms ileri | `1943140` | `1943340` | `1943520` | Geçti |
| `PlcSessionId` sabit | `4` | `4` | `4` | Geçti |
| Hesaplanan CRC = wire CRC | `0xCC62FAA1` | `0x58B6F357` | `0xB28622F9` | Geçti |
| Local reserved `48..59` | Tümü `0` | Tümü `0` | Tümü `0` | Geçti |

## Sayaç ve session davranışı

| Alan | Örnek 1 | Örnek 2 | Örnek 3 | Gözlem |
|---|---:|---:|---:|---|
| `begin_sequence` | `97157` | `97167` | `97176` | İleri |
| `plc_session_id` | `4` | `4` | `4` | Test boyunca sabit |
| `plc_heartbeat_counter` | `97157` | `97167` | `97176` | İleri |
| `plc_monotonic_ms` | `1943140` | `1943340` | `1943520` | `+200`, `+180` ms |
| `accepted_orin_session_id` | `0` | `0` | `0` | Komut akışı yok; sabit |
| `accepted_command_sequence` | `0` | `0` | `0` | Komut akışı yok; sabit |
| `command_age_ms` | `0` | `0` | `0` | Bu PLC durumunda sabit |
| `orin_heartbeat_age_ms` | `0` | `0` | `0` | Bu PLC durumunda sabit |
| `g16_frame_age_ms` | `0` | `0` | `0` | G16 kapalı; sabit |
| `g16_frame_counter` | `0` | `0` | `0` | G16 kapalı; sabit |

Snapshot sequence ve PLC heartbeat aynı publisher çevrim sayacını taşıdı ve
her okumada birlikte ilerledi. PLC session test boyunca değişmedi. Kabul
edilmiş Orin session/command ve G16 frame sayaçlarının sıfırda kalması,
komut akışı ve G16 kapalı test koşuluyla tutarlıdır.

## Decode edilmiş typed alanlar

| Alan | Örnek 1 | Örnek 2 | Örnek 3 |
|---|---:|---:|---:|
| `operational_state` | `8` (`FAULT_LOCKOUT`) | `8` | `8` |
| `active_authority` | `5` (`FAULT_LOCKOUT`) | `5` | `5` |
| `status_flags` | `0x0000` | `0x0000` | `0x0000` |
| `command_reject_reason` | `0` | `0` | `0` |
| `fault_bits` | `0x00000400` | `0x00000400` | `0x00000400` |
| `interlock_bits` | `0x00000123` | `0x00000123` | `0x00000123` |
| `actual_speed_mps` | `0.0` | `0.0` | `0.0` |
| `actual_steering_angle_rad` | `-2.11149693` | `-2.10092545` | `-2.10092545` |
| `throttle_position_percent` | `0.0` | `0.0` | `0.0` |
| `brake_position_percent` | `0.0` | `0.0` | `0.0` |
| `brake_effect_value` | `0.0` | `0.0` | `0.0` |
| `left_wheel_speed_mps` | `0.0` | `0.0` | `0.0` |
| `right_wheel_speed_mps` | `0.0` | `0.0` | `0.0` |
| `g16_summary_flags` | `0x0000` | `0x0000` | `0x0000` |
| `safety_summary_flags` | `0x0005` | `0x0005` | `0x0005` |

`status_flags=0x0000` olduğundan actual speed, steering, throttle, brake,
wheel speed, G16, active config ve diğer status validity bitlerinin tamamı
kapalıdır. Bu nedenle ham `actual_steering_angle_rad` değeri üretim feedback'i
olarak tüketilmemelidir.

`g16_summary_flags=0x0000`, G16 kapalıyken G16 geçerlilik bitlerinin kapalı
olması beklentisiyle uyumludur. Gözlenen safety durumu da güvenlidir:

- `fault_bits=0x00000400`: `SAFETY_CHAIN_FAULT` açık.
- `interlock_bits=0x00000123`: `ESTOP_ACTIVE`,
  `SAFETY_RELAY_NOT_HEALTHY`, `STEERING_NOT_READY` ve
  `MANUAL_G16_INVALID` açık.
- `safety_summary_flags=0x0005`: `ESTOP_ACTIVE` ve
  `DRIVE_INHIBIT_ACTIVE` açık.
- PLC `FAULT_LOCKOUT` otoritesinde; drive-enabled biti kapalıdır.

## Ham 64-register kanıtı

Aşağıdaki diziler blok-local register `0..63` sırasındadır; her satır sekiz
register içerir.

### Örnek 1

```text
00..07: 5253 0001 0001 0040 0001 7B85 0000 0004
08..15: 0001 7B85 001D A664 0008 0005 0000 0000
16..23: 0000 0400 0000 0123 0000 0000 0000 0000
24..31: 0000 0000 0000 0000 0000 0000 C007 22C4
32..39: 0000 0000 0000 0000 0000 0000 0000 0000
40..47: 0000 0000 0000 0005 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 CC62 FAA1 0001 7B85
```

### Örnek 2

```text
00..07: 5253 0001 0001 0040 0001 7B8F 0000 0004
08..15: 0001 7B8F 001D A72C 0008 0005 0000 0000
16..23: 0000 0400 0000 0123 0000 0000 0000 0000
24..31: 0000 0000 0000 0000 0000 0000 C006 7590
32..39: 0000 0000 0000 0000 0000 0000 0000 0000
40..47: 0000 0000 0000 0005 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 58B6 F357 0001 7B8F
```

### Örnek 3

```text
00..07: 5253 0001 0001 0040 0001 7B98 0000 0004
08..15: 0001 7B98 001D A7E0 0008 0005 0000 0000
16..23: 0000 0400 0000 0123 0000 0000 0000 0000
24..31: 0000 0000 0000 0000 0000 0000 C006 7590
32..39: 0000 0000 0000 0000 0000 0000 0000 0000
40..47: 0000 0000 0000 0005 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 B286 22F9 0001 7B98
```

Local `48..59` alanı her üç ham görüntüde sıfırdır. Local `60..61` CRC ve
`62..63` end sequence alanıdır.

## Nihai kabul

Fiziksel PLC `PLC_STATE` publisher, üç örneğin tamamında:

- doğru PLC_STATE magic/type, protokol ve uzunluk header'ı;
- eş begin/end ve ileri snapshot sequence;
- ileri PLC heartbeat ve monotonic süre;
- test boyunca sabit PLC session kimliği;
- doğru CRC-32/ISO-HDLC;
- sıfır reserved alanlar;
- G16 kapalı koşuluna uygun kapalı G16 validity bitleri

üretti. `PLC_STATE` FC03 publisher fiziksel salt-okunur kabul testini
geçmiştir.

Bu test yalnız `PLC_STATE` yayın bütünlüğünü ve salt-okunur gözlenen durumun
tutarlılığını kabul eder. PLC restartı, boot-retain session değişimi veya eski
Orin command replay reddini kapsamaz; bunlar ayrı kontrollü testtir.

# PLC_DIAGNOSTICS Fiziksel FC03 Kabulü — 21 Ağustos 2026

Bu belge Ana Proje Codex'i tarafından, fiziksel PLC'ye yüklenmiş
`PLC_DIAGNOSTICS` publisher için yapılan salt-okunur Modbus TCP kabul testinin
kanıtı olarak hazırlanmıştır.

Ana proje codec/sözleşme otoritesi:

`rover-core-ros2/agent/local-metric-map@854fee6f67ad3cb37f526c84fbcf79cdcacf10fa`

## Kapsam ve yöntem

| Alan | Değer |
|---|---|
| PLC | `192.168.2.100:502` |
| Modbus unit ID | `1` |
| İşlem | Yalnız FC03 |
| Başlangıç | `192 (0x00C0)` |
| Uzunluk | `64` register |
| Blok | `PLC_DIAGNOSTICS` |
| Protokol | `1.1` |
| Beklenen magic | `0x5244` |
| Codec | Ana ROS `rover_hardware.plc_protocol` |

Tek `ModbusTcpClient` nesnesiyle bir TCP bağlantısı açıldı, aynı kalıcı
session üzerinden 300 ms aralıklı üç FC03 okuması yapıldı ve bağlantı test
sonunda kapatıldı. PLC'ye FC16 veya başka bir yazma isteği gönderilmedi. PLC
programı ve TIA projesi değiştirilmedi/download edilmedi.

Ana ROS `decode_block()` her örnekte header, begin/end, reserved alan ve CRC
doğrulamasından geçti. Progression ayrıca `is_newer_sequence()` modulo-`2^32`
karşılaştırmasıyla kontrol edildi.

## Zorunlu kabul kontrolleri

| Kontrol | Örnek 1 | Örnek 2 | Örnek 3 | Karar |
|---|---:|---:|---:|---|
| Magic | `0x5244` | `0x5244` | `0x5244` | Geçti |
| Protocol major/minor | `1/1` | `1/1` | `1/1` | Geçti |
| Block length | `64` | `64` | `64` | Geçti |
| Begin = end | `12929` | `12940` | `12950` | Geçti |
| Sequence ileri | Başlangıç | `12929 -> 12940` | `12940 -> 12950` | Geçti |
| Diagnostic heartbeat ileri | `12929` | `12940` | `12950` | Geçti |
| Hesaplanan CRC = wire CRC | `0x88B1BB2F` | `0xBB99C751` | `0x0952C2E3` | Geçti |
| Local reserved `50..59` | Tümü `0` | Tümü `0` | Tümü `0` | Geçti |

## Decode edilmiş typed alanlar

| Alan | Örnek 1 | Örnek 2 | Örnek 3 |
|---|---:|---:|---:|
| `begin_sequence` | `12929` | `12940` | `12950` |
| `plc_session_id` | `3` | `3` | `3` |
| `diagnostic_heartbeat` | `12929` | `12940` | `12950` |
| `plc_monotonic_ms` | `258580` | `258800` | `259000` |
| `scan_time_us` | `6509` | `6683` | `7518` |
| `max_scan_time_us` | `17687` | `17687` | `17687` |
| `diagnostic_flags` | `0x0173` | `0x0173` | `0x0173` |
| `mb_server_status` | `0x7002` | `0x7006` | `0x7006` |
| `esp_mb_client_status` | `0x7006` | `0x7005` | `0x7006` |
| `last_command_reject_reason` | `6` | `6` | `6` |
| `orin_command_accept_count` | `0` | `0` | `0` |
| `orin_command_reject_count` | `0` | `0` | `0` |
| `orin_crc_error_count` | `0` | `0` | `0` |
| `orin_protocol_error_count` | `0` | `0` | `0` |
| `orin_timeout_count` | `1` | `1` | `1` |
| `esp_poll_success_count` | `14687` | `14698` | `14707` |
| `esp_poll_error_count` | `0` | `0` | `0` |
| `esp_crc_error_count` | `0` | `0` | `0` |
| `esp_stale_count` | `0` | `0` | `0` |
| `g16_invalid_frame_count` | `3` | `3` | `3` |
| `g16_frame_lost_count` | `0` | `0` | `0` |
| `g16_failsafe_count` | `0` | `0` | `0` |
| `controlled_stop_count` | `0` | `0` | `0` |
| `fault_transition_count` | `0` | `0` | `0` |
| `output_write_violation_count` | `0` | `0` | `0` |
| `crc32` | `0x88B1BB2F` | `0xBB99C751` | `0x0952C2E3` |
| `end_sequence` | `12929` | `12940` | `12950` |

`scan_time_us` üç örnekte `4000..8000 us` beklenen aralığındadır.
`max_scan_time_us=17687` online gözlemle uyumludur. Orin command stream kapalı
olduğu için `last_command_reject_reason=6 (HEARTBEAT_STALE)` ve
`orin_timeout_count=1` beklenen sonuçtur.

ESP poll başarı sayacı iki örnek aralığında sırasıyla `+11` ve `+9` ilerledi.
ESP poll, CRC ve stale hata sayaçları sıfır kaldı. G16 invalid/lost/failsafe
sayaçları ESP'den gelen lifetime değerleridir; bu okumada `3/0/0` görüldü.

## DiagnosticFlags doğrulaması

Üç örnekte de `diagnostic_flags = 0x0173` (`0000 0001 0111 0011`) okundu.

| Bit | Ad | Beklenen | Okunan | Karar |
|---:|---|---|---|---|
| 0 | `SCAN_TIME_VALID` | Açık | Açık | Geçti |
| 1 | `ORIN_SERVER_RUNNING` | Açık | Açık | Geçti |
| 2 | `ESP_CLIENT_CONNECTED` | Kapalı | Kapalı | Geçti |
| 3 | `ORIN_COMMAND_FRESH` | Kapalı | Kapalı | Geçti |
| 4 | `ESP_SNAPSHOT_FRESH` | Açık | Açık | Geçti |
| 5 | `G16_FRAME_FRESH` | Açık | Açık | Geçti |
| 6 | `SAFETY_INPUTS_VALID` | Açık | Açık | Geçti |
| 7 | `ACTUATOR_FEEDBACK_VALID` | Kapalı | Kapalı | Geçti |
| 8 | `COUNTERS_VALID` | Açık | Açık | Geçti |
| 9 | `OUTPUT_WRITE_VIOLATION` | Kapalı | Kapalı | Geçti |

`ESP_CLIENT_CONNECTED` bitinin kapalı olması, mevcut Siemens wrapper'ın gerçek
connected çıkışı sunmaması nedeniyle bilinçli ve konservatif davranıştır.
`ACTUATOR_FEEDBACK_VALID`, mekanik feedback tamamlanmadığı için kapalıdır.

## Ham 64-register kanıtı

Aşağıdaki diziler blok-local register `0..63` sırasındadır; her satır sekiz
register içerir.

### Örnek 1

```text
00..07: 5244 0001 0001 0040 0000 3281 0000 0003
08..15: 0000 3281 0003 F214 0000 196D 0000 4517
16..23: 0173 7002 7006 0006 0000 0000 0000 0000
24..31: 0000 0000 0000 0000 0000 0001 0000 395F
32..39: 0000 0000 0000 0000 0000 0000 0000 0003
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 88B1 BB2F 0000 3281
```

### Örnek 2

```text
00..07: 5244 0001 0001 0040 0000 328C 0000 0003
08..15: 0000 328C 0003 F2F0 0000 1A1B 0000 4517
16..23: 0173 7006 7005 0006 0000 0000 0000 0000
24..31: 0000 0000 0000 0000 0000 0001 0000 396A
32..39: 0000 0000 0000 0000 0000 0000 0000 0003
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 BB99 C751 0000 328C
```

### Örnek 3

```text
00..07: 5244 0001 0001 0040 0000 3296 0000 0003
08..15: 0000 3296 0003 F3B8 0000 1D5E 0000 4517
16..23: 0173 7006 7006 0006 0000 0000 0000 0000
24..31: 0000 0000 0000 0000 0000 0001 0000 3973
32..39: 0000 0000 0000 0000 0000 0000 0000 0003
40..47: 0000 0000 0000 0000 0000 0000 0000 0000
48..55: 0000 0000 0000 0000 0000 0000 0000 0000
56..63: 0000 0000 0000 0000 0952 C2E3 0000 3296
```

Local `50..59` alanı her üç ham görüntüde sıfırdır. Local `60..61` CRC ve
`62..63` end sequence alanıdır.

## Nihai kabul

Fiziksel PLC `PLC_DIAGNOSTICS` publisher, istenen üç örneğin tamamında:

- doğru magic/protokol/uzunluk header'ı;
- eş begin/end ve ileri sequence;
- ileri diagnostic heartbeat;
- doğru CRC-32/ISO-HDLC;
- sıfır reserved alan;
- beklenen diagnostic flag deseni;
- ilerleyen ESP poll başarı sayacı ve sıfır ESP haberleşme hata sayaçları

üretti. `PLC_DIAGNOSTICS` FC03 publisher fiziksel salt-okunur kabul testini
geçmiştir.

Bu kabul publisher/protokol görünürlüğünü kapsar. Output-write-violation
detector, gerçek aktüatör feedback'i ve mekanik/odometry kabulü kapsam dışıdır.

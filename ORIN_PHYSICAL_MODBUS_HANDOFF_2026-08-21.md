# Orin Fiziksel Modbus Handoff — 21 Ağustos 2026

`FB_OrinCommandSnapshotValidator V0.6` için normal re-arm, held-TRUE yarış
koruması, duplicate/backward progression, uint32 wrap ve frozen-command
fiziksel kabul sonuçları
[`ORIN_COMMAND_VALIDATOR_V06_PHYSICAL_ACCEPTANCE_2026-08-21.md`](ORIN_COMMAND_VALIDATOR_V06_PHYSICAL_ACCEPTANCE_2026-08-21.md)
belgesinde kayıtlıdır.

Bu belge PLC Codex'i için Ana Proje Codex'i tarafından hazırlanmıştır. Kaynak
otorite
`rover-core-ros2/agent/local-metric-map@854fee6f67ad3cb37f526c84fbcf79cdcacf10fa`
commit'idir.

Ana proje tarafındaki değişiklikler:

- tek sahipli kalıcı Modbus TCP session;
- aynı session içinde sıralı FC16 command ve FC03 state erişimi;
- PLC accepted session/sequence, reject reason ve link-valid doğrulaması;
- acknowledgement timeout ve sequence progression takibi;
- gerçek PLC davranışına uygun açık session re-arm isteyen mock PLC;
- fiziksel bench kaydı ve 135/135 geçen `rover_hardware` test paketi.

Bu PLC deposunda Ana Proje Codex'i SCL, Python bench scripti veya TIA proje
kodu değiştirmemiştir. Aşağıdaki maddeler fiziksel test kanıtı ve PLC tarafı
sonraki iş yönlendirmesidir.

## 1. Doğrulanan fiziksel topoloji

| Uç | Adres | Sonuç |
|---|---|---|
| VM PLC adaptörü | `192.168.2.10/24` | UP |
| PLC | `192.168.2.100/24` | ping 3/3 |
| PLC Modbus TCP | `192.168.2.100:502` | açık |

Üretim `plc_bridge_node`, fiziksel PLC'nin tek `MB_SERVER` bağlantı
davranışıyla uyumlu olarak tek kalıcı TCP session kullandı. Komut ve state
adapterlerinin ayrı bağlantılarla yarışması kaldırıldı.

## 2. Fiziksel FC16/FC03 kabul sonucu

Test boyunca PLC `MANUAL` otoritesinde kaldı; hız ve direksiyon hedefleri
sıfırdı ve fiziksel hareket oluşmadı.

### Aşama A — session re-arm

Yeni Orin session görüldüğünde PLC beklenen sonucu üretti:

- reject `5 (SESSION_CHANGED_REARM_REQUIRED)`;
- interlock `AUTHORITY_REARM_REQUIRED`;
- accepted session/sequence `0/0`.

TIA üzerinden validator `SessionRearm` girişine, session görüldükten sonra
`FALSE -> TRUE -> FALSE` darbesi uygulandı. Accepted session güncellendi ve
re-arm interlock'u temizlendi. Re-arm Modbus payload'una eklenmedi; bu güvenlik
sınırı korunmalıdır.

### Aşama B — SAFE_DISABLED command flags

İlk Orin generator sürümü `SAFE_DISABLED` için flags `0` gönderdi. Validator
V0.5 bütün modlarda `COMMAND_VALID` bitini zorunlu tuttuğu için reject
`3 (INVALID_SNAPSHOT)` verdi.

Ana sözleşme ve generator şu kurala güncellendi:

```text
requested_mode = SAFE_DISABLED
command_flags = COMMAND_VALID (0x0001)
target_speed_mps = 0.0
target_steering_angle_rad = 0.0
```

PLC validator'ın mevcut davranışı bu sözleşmeyle uyumludur.

### Aşama C — bench motion/config limiti

`mission_speed_limit_mps=4.0`, mevcut commissioning çağrısındaki
`MaxMissionSpeedMps=2.0` sınırını aştığı için reject
`10 (VALUE_OUT_OF_RANGE)` görüldü. Bridge parametresi `2.0` yapıldı.

Son başarılı akış:

- `/health/plc_command_link=true`;
- `/plc/command_acceptance_reason=command_acknowledged`;
- accepted command sequence canlı olarak ilerledi;
- command flags `0x0001`;
- fault/interlock `0`;
- PLC `MANUAL`, hedef hız/direksiyon `0.0`.

Bridge durdurulduktan sonra reject `6 (HEARTBEAT_STALE)` ve heartbeat age
`500 ms` görülmesi beklenen fail-safe timeout davranışıdır. Son raw command
sequence `1536`, accepted sequence `1535` idi; bir PLC çevrimlik ACK gecikmesi
normal kabul edildi.

## 3. PLC Codex'i için gerekli takip işleri

### P1 — ACTUAL_SPEED_VALID ve wheel odometry

Bridge sonrası state flags `0x0502` oldu. `STEERING_ANGLE_VALID=1`, fakat
`ACTUAL_SPEED_VALID=0` kaldığı için ROS wheel odometry bilinçli olarak
yayınlanmadı.

PLC tarafında:

1. gerçek hız feedback kaynağını ve ölçeğini kesinleştir;
2. feedback freshness/range doğrulamasını uygula;
3. yalnız doğrulanmış değerle `ACTUAL_SPEED_VALID=1` üret;
4. mümkünse sol/sağ wheel validity ve hızlarını da aynı kuralla yayımla;
5. feedback geçersizken sıfır değeri geçerliymiş gibi işaretleme.

### P1 — SessionRearm commissioning tag'i

`SessionRearm` girişi fiziksel testte çalıştı. PLC Codex'i:

- kullanılan gerçek TIA tag/DB yolunu commissioning belgesine yazmalı;
- darbenin session görüldükten sonra uygulanması şartını korumalı;
- input TRUE tutulduğunda gelecekteki session'ı kabul etmemeli;
- watch table/HMI akışında `FALSE -> TRUE -> FALSE` kenarını görünür yapmalı;
- bu girişi Orin command Modbus payload'una taşımamalı.

### P1 — Aktif limitlerin yayınlanması

Fiziksel test, Orin launch parametresi ile PLC commissioning limiti farklıysa
geçerli command snapshot'ın reject `10` aldığını gösterdi. `ACTIVE_CONFIG`
publisher tamamlandığında Orin:

- PLC'nin etkin limitlerini salt-okunur almalı;
- kendi gönderdiği limitlerin PLC üst sınırını aşmadığını doğrulamalı;
- `ACTIVE_CONFIG_VALID=0` iken AUTO'yu açmamalı.

Mevcut `ACTIVE_CONFIG` bloğu canlı FC03 okumada sıfırdır; bu publisher hâlâ
tamamlanmalıdır.

### P2 — Diagnostics görünürlüğü

ROS acceptance takipçisi artık kritik PLC reject reason'ını accepted sequence
henüz sıfırken de acknowledgement timeout'tan önce raporlar. PLC tarafında
`PLC_DIAGNOSTICS` publisher tamamlanarak en az şu alanlar canlı yapılmalıdır:

- command accept/reject sayaçları;
- son reject reason;
- heartbeat/command timeout sayaçları;
- session/re-arm olayları;
- output write violation;
- transport ve scan diagnostics.

## 4. Korunacak güvenlik sonucu

- Başarılı FC16 cevabı hareket kabulü değildir.
- Sağlıklı Orin command link için accepted session, ilerleyen accepted
  sequence, `ORIN_COMMAND_LINK_VALID` ve reject reason birlikte doğrulanır.
- PLC nihai authority ve interlock sahibidir.
- Re-arm harici ve bilinçli bir commissioning/operator eylemidir.
- AUTO, mevcut uygulama aşamasında kapalı kalmalıdır.
- Hız feedback validity tamamlanmadan ROS wheel odometry sağlıklı sayılamaz.

Ana projedeki ayrıntılı ham bench kaydı:
`docs/PLC_FIZIKSEL_MODBUS_BENCH_2026-08-21.md`.

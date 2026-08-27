# 192.168.144.0/24 Ortak Araç Ağına Geçiş

Durum: **fiziksel kabul tamamlandı (27 Ağustos 2026)**. Ortak araç ağı
`192.168.144.0/24` olarak devreye alınmıştır.

## Amaç

G16 alıcısı ve IP kameranın mevcut ağı ile PLC, ESP32 gateway ve Orin'i aynı
Ethernet switch üzerinde birleştirmek. G16 kamera/LAN çıkışına takılan korumalı
Ethernet soketiyle hem kameraya hem alıcıya erişim ve ping doğrulanmıştır.

## Planlanan adresler

| Cihaz | Planlanan adres |
|---|---|
| Orin / entegrasyon VM'i | `192.168.144.10/24` |
| G16 alıcısı | `192.168.144.11/24` |
| PLC CPU 1214C | `192.168.144.100/24` |
| IP kamera | `192.168.144.108/24` |
| ESP32 G16 gateway | `192.168.144.166/24` |

Tüm cihazlarda subnet maskesi `255.255.255.0` olmalıdır. Yalnız aynı subnet
içindeki trafik için default gateway gerekmez. Router üzerinden başka ağlara
erişim istenirse gerçek router adresi ayrıca tanımlanmalıdır; eski firmware
gateway değeri `192.168.2.241` yeni ağın gateway'i veya PLC adresi değildir.

## PLC değişiklikleri

1. CPU PROFINET IPv4 adresini `192.168.144.100/24` yap.
2. Donanım konfigürasyonunu PLC'ye indir ve yeni adresten erişimi doğrula.
3. ESP firmware'i yeni adrese taşındıktan sonra `FB_EspGatewayClient`
   bağlantısındaki `RemoteAddress` değerini `192.168.144.166` yap.
4. `InterfaceId=64`, Modbus portları, MB_SERVER alanları ve teknoloji objesi
   ayarları ağ geçişi nedeniyle değiştirilmez.

PLC'de ayrıca router/gateway tanımlamak, aynı `/24` subnet içindeki ESP, Orin,
G16 veya kamera erişimi için gerekli değildir.

## Kontrollü geçiş sırası

1. Bakım bilgisayarına geçici ve benzersiz bir `192.168.144.x/24` adresi ver.
2. PLC'yi `192.168.144.100/24` yap; ping, online erişim ve TCP/502'yi doğrula.
3. ESP firmware'ini `192.168.144.166/24` için güncelle; eski
   `192.168.2.241` gateway ayarını kaldır veya gerçek gateway ile değiştir.
4. PLC ESP `RemoteAddress` alanını `192.168.144.166` yap ve G16 snapshot
   haberleşmesini yeniden kabul et.
5. Orin/VM PLC hedefini `192.168.144.100` yap; PLC_STATE, PLC_DIAGNOSTICS ve
   ACTIVE_CONFIG bloklarını FC03 ile yeniden doğrula.
6. G16 ve kamerayı switch'e ekle; ping ile birlikte kamera RTSP akışını test et.
7. Aynı switch üzerindeki kamera trafiği çalışırken Modbus timeout, CRC ve stale
   sayaçlarında artış olmadığını kontrol et.

## Kabul ölçütleri

- Beş cihazın IP adresleri benzersizdir ve doğru `/24` maskesindedir.
- PLC, ESP, Orin/VM, G16 ve kamera karşılıklı olarak gereken hedeflere erişir.
- ESP snapshot CRC/sequence/frame freshness testleri yeniden geçer.
- Orin Modbus command ve PLC publisher FC03 testleri yeniden geçer.
- Kamera RTSP akışı açıkken PLC scan süresi ve haberleşme hata sayaçları kabul
  sınırlarında kalır.
- Ağ geçişi hiçbir actuator yetkisi veya hareket izni üretmez.

## Tarihsel kanıtlar

Önceki fiziksel kabul belgelerindeki `192.168.2.x` adresleri test anındaki
tarihsel kanıtlardır ve değiştirilmemelidir. Yeni ağın ayrıntılı kabul kanıtı
ana ROS deposunda tutulur; sonucu aşağıda özetlenmiştir.

## Fiziksel kabul sonucu — 27 Ağustos 2026

Ana proje Codex'i tarafından VM–PLC–ESP–G16–kamera zinciri yeni ağda fiziksel
olarak doğrulandı:

- PLC hedefi `192.168.144.100:502`, Modbus Unit ID `1`;
- PLC session `9`, yeni Orin session `2070343649`;
- temiz re-arm kabul edildi, command link `healthy` oldu;
- son reject `NONE_ACCEPTED`, sayaçlar ilerledi;
- hız hedefi ve okunan hız `0.0 m/s` kaldı;
- fault/interlock görülmedi ve AUTO gönderilmedi;
- üç VM servisi aktif, systemd testleri `3/3` geçti;
- PLC–ESP–G16 ve kamera aynı `192.168.144.0/24` switch ağında çalıştı.

Ana ROS kabul kanıtı:

- depo/dal: `rover-core-ros2`, `agent/local-metric-map`;
- commit: `80febf3`;
- belge: `docs/VM_144_NETWORK_PHYSICAL_ACCEPTANCE_2026-08-27.md`.

Re-arm çevresinde görülen iki kısa ACK/stale geçişi kendiliğinden toparlandı ve
ana kabul belgesinde kanıt olarak tutuldu.

Geçerli G16 nedeniyle PLC'nin `MANUAL / MANUAL` kalması mevcut bağımsız manuel
otorite tasarımına uygundur. Orin'in `SAFE_DISABLED` isteği manuel otoriteyi
zorla bastırmaz. Bu nedenle mekanik/aktüatör devreye alma tamamlanana kadar
fiziksel drive enerjisi kapalı veya güvenli biçimde inhibit edilmiş tutulmalıdır.

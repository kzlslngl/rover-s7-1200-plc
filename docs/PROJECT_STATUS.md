# Proje Durumu

Son güncelleme: 2026-08-13

## Doğrulanan temel bilgiler

- TIA Portal proje biçimi: V20 (`Rover_PLC.ap20`, `ProjectVersion=20.0.0.0`)
- Başlangıç projesi: `tia/RoverPLC/Rover_PLC.ap20`
- Proje durumu: boş başlangıç projesi; hareket mantığı ve fiziksel çıkış yok
- Hedef CPU: Siemens S7-1200 CPU 1214C DC/DC/DC
- Sipariş numarası: `6ES7 214-1AG40-0XB0`
- Katalog firmware seviyesi: V4.7
- Fiziksel CPU'da yüklü firmware: V4.6
- Yerleşik I/O: 14 DI 24 V DC, 10 DO 24 V DC, 2 AI 0-10 V DC
- Program/veri belleği: 150 KB
- Protokol hedefi: Modbus TCP v1.1

## Geçici bench ağı

- PLC: `192.168.2.100/24`
- ESP32 gateway: `192.168.2.166/24`
- ESP Modbus TCP: port `502`, Unit ID `1`
- ESP wire register aralığı: offset `320`, uzunluk `64`
- Siemens `MB_CLIENT` adresi: `40321`, uzunluk `64`, `MB_MODE=0` (FC03)

Bu adresler bench değerleridir ve production IP planı olarak kabul edilmez.

## Donanım doğrulama kapısı

Aşağıdaki bilgiler fiziksel CPU etiketi, TIA Portal **Device configuration** görünümü
veya güvenilir donanım envanteri üzerinden doğrulanmadan PLC kodunda donanıma bağlı
seçim yapılmayacaktır:

- Sinyal/iletişim modüllerinin sipariş numaraları ve firmware sürümleri
- PROFINET arayüzü ve statik IP planı

Siemens'in güncel ürün veri sayfası bu sipariş numarası için firmware V4.7 ve
STEP 7 V20 veya üzerini belirtmektedir. Bu değer proje için hedef donanım katalog
seviyesidir; fiziksel CPU'da gerçekten yüklü sürüm TIA Portal **Online &
diagnostics** ekranından okunana kadar doğrulanmış sayılmaz.

## İlk geliştirme aşaması kontrol listesi

- [x] TIA Portal sürümünü kaydet (V20)
- [x] CPU kesin sipariş numarasını kaydet
- [x] Fiziksel CPU'da yüklü firmware sürümünü doğrula (V4.6)
- [x] Boş CPU projesini depoya al
- [ ] Ham transport DB'lerini tanımla
- [ ] Protokol enum/bitfield sabitlerini ve typed UDT'leri oluştur
- [x] CRC-32/ISO-HDLC ve endian yardımcılarını SCL olarak yaz
- [ ] Ortak test vektörlerini PLC watch table veya test FB ile doğrula
- [x] G16 snapshot validator'ını diagnostics/watch-only olarak yaz
- [x] G16 validator'ını TIA V20'de compile edip canlı snapshot ile doğrula
- [ ] G16 kanal mapping ve min/nötr/max değerlerini ölç
- [ ] Orin command snapshot validator'ını diagnostics/watch-only olarak yaz
- [ ] Negatif ve sınır durum enjeksiyon testlerini çalıştır

Bu aşama tamamlanana kadar authority state machine, ESP `MB_CLIENT` donanım
bağlantısı ve aktüatör çıkışları eklenmeyecektir.

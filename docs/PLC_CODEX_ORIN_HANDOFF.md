# PLC Codex -> Ana Proje Codex Orin Entegrasyon Notu

Kaynak: **PLC Codex**, `rover-s7-1200-plc` bench entegrasyon calismasi.

Bu belge, ana rover/Orin projesinde calisan Codex'in PLC tarafinda gercek CPU
uzerinde dogrulanmis mevcut protokol durumunu ve sonraki VM testlerini yanlis
varsayim yapmadan devralmasi icin hazirlanmistir.

## Dogrulanmis bench topolojisi

- PLC: Siemens S7-1200 CPU 1214C DC/DC/DC, `6ES7 214-1AG40-0XB0`
- CPU firmware: V4.6
- TIA Portal: V20
- PLC bench IP: `192.168.2.100/24`
- ESP32 G16 gateway bench IP: `192.168.2.166/24`
- PLC Modbus TCP server: TCP port `502`, Unit ID `1`
- Orin yerine kullanilacak VM: ayni `192.168.2.0/24` aginda, benzersiz IP

VM ag adaptoru bridged/kopru modunda olmalidir. NAT arkasinda kalan VM'nin
PLC'ye dogrudan erisecegi varsayilmamalidir.

## PLC Modbus holding register haritasi

| Offset | Uzunluk | Blok | Yon |
|---:|---:|---|---|
| `0` | 64 | `ORIN_TO_PLC_COMMAND` | Orin/VM -> PLC, tek FC16 |
| `64` | 64 | `PLC_TO_ORIN_STATE` | PLC -> Orin/VM, tam FC03 |
| `128` | 64 | `G16_STATUS` | PLC -> Orin/VM, tam FC03 |
| `192` | 64 | diagnostics | PLC -> Orin/VM |
| `256` | 64 | active config | PLC -> Orin/VM |

Snapshot bloklari protokol `1.1` ve 64 register uzunlugundadir. Okuyucu:

1. begin/end sequence esitligini,
2. register `0..59` uzerindeki CRC-32/ISO-HDLC sonucunu,
3. magic, protocol ve block-length alanlarini

her okumada dogrulamalidir. Bir FC03 cevabi almak tek basina snapshot kabul
etmek icin yeterli degildir.

## VM salt-okuma testi

PLC ve publisher bloklari acikken VM'den:

```bash
ping 192.168.2.100
python3 scripts/test_orin_modbus_fc03.py 192.168.2.100 64 64
python3 scripts/test_orin_modbus_fc03.py 192.168.2.100 128 64
```

Her iki Python testinde de su sonuc beklenir:

```text
header_ok=True sequence_ok=True crc_ok=True
```

`64..127` PLC state, `128..191` ise G16 status snapshot'idir.

## VM command-stream testi

Mevcut bench komut ureticisi:

```bash
python3 scripts/stream_orin_command_fc16.py 192.168.2.100 300 normal
```

Bu profil her 100 ms'de artan snapshot sequence, heartbeat ve command sequence
ile `CONTROLLED_STOP` komutu gonderir. Yeni Orin session PLC tarafinda once
`SessionRearmRequired=TRUE` olusturur. Session goruldukten sonra PLC re-arm
girisine yeni bir `FALSE -> TRUE -> FALSE` darbesi verilmelidir.

Basarili re-arm ve akista beklenen PLC validator sonuclari:

- `SnapshotValid=TRUE`
- `HeartbeatFresh=TRUE`
- `CommandFresh=TRUE`
- `PayloadValid=TRUE`
- `CommandValidityFresh=TRUE`
- `DataValid=TRUE`
- `RejectReason=0`

Akis kesildiginde command ve heartbeat freshness zaman asimina ugramali,
`DataValid` tekrar `FALSE` olmalidir.

## Guvenlik ve yetki sinirlari

- Modbus baglantisi veya basarili FC16 yazimi hareket izni degildir.
- PLC raw register alanlarini actuator mantiginda dogrudan kullanmaz.
- Yalniz validator'dan gecmis typed command kullanilabilir.
- Mevcut bench validator yalniz `SAFE_DISABLED` ve `CONTROLLED_STOP`
  komutlarini kabul eder.
- AUTO komutlari autonomy/safety guard entegrasyonu tamamlanana kadar kapali
  kalir.
- Orin dogrudan pulse/direction, servo enable, gaz, fren veya safety cikisi
  surmez; fiziksel komutu ve son limitlemeyi PLC yapar.
- G16 status Orin'e izleme, operator durumu ve safety context icin PLC
  uzerinden yayinlanir. Orin bu veriyi dogrudan actuator komutuna cevirmemelidir.

> **Dipnot - mevcut AUTO steering durumu:** Orin komut transportu ve validator
> calisiyor olsa da Orin su anda direksiyon servosunu AUTO modda kontrol edemez.
> Validator bench asamasinda yalniz `SAFE_DISABLED` ve `CONTROLLED_STOP`
> mode'larini kabul eder; AUTO komutlari `RejectReason=11` ile kapali tutulur.
> Validated `TargetSteeringAngleRad` henuz steering supervisor hareket yoluna
> bagli degildir ve authority tarafindaki Orin validity baglantisi production
> kaynagi olarak tamamlanmamistir. AUTO hareket acilmadan once hedef radyandan
> dereceye cevrilmeli, PLC mekanik aci/rate limitleriyle sinirlanmali ve
> `AutoCommandValid`; validated command, AUTO authority ve safety kosullarinin
> birlikte saglanmasindan uretilmelidir. Ilk entegrasyon watch-only yapilmali;
> hedef, yon, donusum, session ve timeout davranisi dogrulanmadan servo hareket
> yoluna baglanmamalidir.

## Zamanlama bilgisi

`PLC_TO_ORIN_STATE` ve `G16_STATUS` publisher bloklari IEC `TON` ile nominal
`20 ms` periyotta yayin yapar. OB1 scan suresi sabit kabul edilmez. Canli bench
olcumunde yaklasik degerler:

- tipik scan: `5.4..5.6 ms`
- gozlenen minimum: yaklasik `4.35 ms`
- gozlenen maksimum: yaklasik `14.68 ms`

Bu degerler kapasite/diagnostic bilgisidir; Orin freshness hesabi publisher
sequence, heartbeat ve kendi monotonic saatiyle yapilmalidir.

## Mevcut G16 status siniri

G16 status icinde session, heartbeat, SBUS frame counter/age/flags,
channel-valid mask ve 16 ham kanal yayinlanir. `channel_normalized[16]` signed
INT ve nominal `-1000..+1000` olarak tanimlidir; ancak typed kalibrasyon modeli
tamamlanana kadar sifir yayinlanir. Calibration/link-quality/RSSI validity
bitleri bu asamada kapali kalir.

## PLC proje kurali

FB instance DB kaynaklari ayrica teslim edilmeyecektir. TIA, FB OB1'e
eklendiginde kendi `FB_..._DB` instance'ini olusturur. Yalniz global model,
status, raw-register ve retain DB'leri SCL kaynagi olarak tutulur.

## Ana proje icin sonraki isler

1. VM'den iki read-only FC03 snapshot testini calistir.
2. VM'den controlled-stop FC16 stream ve re-arm akisini dogrula.
3. PLC session degisimini okuyucuda yeni boot olarak ele al.
4. TCP kesilmesi/yeniden baglanma ve frozen-command testlerini calistir.
5. PLC state ve G16 status icin Orin tarafinda typed decoder ekle.
6. AUTO komutu uretimini PLC autonomy/safety guard sozlesmesi tamamlanana kadar
   hareket yoluna baglama.

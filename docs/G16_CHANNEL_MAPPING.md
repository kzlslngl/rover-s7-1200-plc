# G16 Kanal Keşfi ve Mapping

Bu aşama yalnızca kumanda kanallarını tanımlar. Hiçbir değer motor, fren,
direksiyon veya başka bir fiziksel çıkışa bağlanmaz.

## Gözlem bloğu

`exported/blocks/FB_G16ChannelObserver.scl` dosyasını import et, compile et ve
ayrı bir instance DB ile OB1'de çağır:

```text
Enable          := TRUE
Reset           := G16ObserverReset
DataValid       := DB_ValidatedG16Input.Data.Valid
ChannelRaw      := DB_ValidatedG16Input.Data.ChannelRaw
ChangeThreshold := 20
```

`Reset` normalde `FALSE` kalır. Her yeni kontrolü ölçmeden önce bir scan
`TRUE`, sonra tekrar `FALSE` yaparak min/max geçmişini temizle.

## Keşif sırası

Kumanda güvenli ve aktüatörlerden ayrılmış durumdayken her kontrolde:

1. Bütün stick/anahtarları nötr konuma al.
2. `Reset` girişine bir darbe ver.
3. Yalnız bir kontrolü yavaşça bir uçtan diğer uca hareket ettir.
4. `MostChangedChannel`, `ChangedMask`, `Minimum[]` ve `Maximum[]` değerlerini
   kaydet.
5. Kontrolü nötre getirip nötr ham değerini kaydet.
6. Aynı işlemi sıradaki kontrol için tekrarla.

## Kayıt tablosu

| Fonksiyon | Kanal index | Minimum | Nötr | Maximum | Yön ters mi? | Anahtar konumları |
|---|---:|---:|---:|---:|---|---|
| İleri/geri stick |  |  |  |  |  |  |
| Direksiyon stick |  |  |  |  |  |  |
| Manual enable |  |  |  |  |  |  |
| Hız modu |  |  |  |  |  |  |
| Kontrollü duruş |  |  |  |  |  |  |

Mapping ve kalibrasyon değerleri bu tablo doldurulmadan PLC kontrol mantığında
sabitlenmeyecektir.

## 2026-08-13 doğrulanan kumanda fiziksel mapping'i

Bu tablo yalnızca G16 üzerindeki fiziksel kontrolleri tanımlar; henüz rover
hareket fonksiyonlarını tanımlamaz.

| Index | Kumanda kontrolü | Ham değer/konum | Durum |
|---:|---|---|---|
| 0 | Joystick X2 | `282 / 1002 / 1722` | bildirildi |
| 1 | Joystick Y2 | `282 / 1002 / 1722` | ortak eksen aralığı varsayımı |
| 2 | Joystick Y1 | `282 / 1002 / 1722` | ortak eksen aralığı varsayımı |
| 3 | Joystick X1 | `282 / 1002 / 1722` | ortak eksen aralığı varsayımı |
| 4 | SW1, 3 konumlu | `282 / 1002 / 1722` | bildirildi |
| 5 | SW2, 3 konumlu | `282 / 1002 / 1722` | bildirildi |
| 6 | SW3, 3 konumlu | `282 / 1002 / 1722` | bildirildi |
| 7 | SW4, 3 konumlu | `282 / 1002 / 1722` | bildirildi |
| 8 | A/B/C/D/E/F buton seçimi | `426 / 685 / 858 / 1074 / 1290 / 1578` | bildirildi |
| 9 | MOD, 2 konumlu | `282 / 1722` | bildirildi |
| 10 | AUX1 pot | `282..1722` | ortak analog aralık varsayımı |
| 11 | AUX2 pot | `282..1722` | ortak analog aralık varsayımı |
| 12 | Joystick X3 | `282 / 1002 / 1722` | ortak eksen aralığı varsayımı |
| 13 | Joystick Y3 | `282 / 1002 / 1722` | ortak eksen aralığı varsayımı |
| 14 | Bilinmiyor/boş | — | kullanılmayacak |
| 15 | Bilinmiyor/boş | — | kullanılmayacak |

Varsayılan analog aralıklar min/nötr/max ölçümüyle doğrulanmalıdır.

## Kullanılan operatör arayüzü

İlk sürümde yalnız aşağıdaki kontroller işlev üretir:

| Kontrol | İşlev |
|---|---|
| MOD | `OperatorEnable` |
| SW1 `-1/0/+1` | controlled stop / manual G16 / auto Orin |
| SW2 `-1/0/+1` | sol gaz-sağ yön / layout kapalı / sağ gaz-sol yön |
| AUX1 | manuel hız ölçeği `0.0..1.0` |
| AUX2 | direksiyon hassasiyeti `0.0..1.0` |
| Joy Y1 ve Joy X2 | sol gaz-sağ yön layout'u |
| Joy Y2 ve Joy X1 | sağ gaz-sol yön layout'u |

SW3, SW4, A–F kalıcı seçici kanalı, Joy X3/Y3 ve kanal 14/15 reserve'dir;
hiçbir operasyonel komut üretmez. A–F kanalı kalıcı değer tuttuğu için korna
gibi momentary görevlerde kullanılmayacaktır.

Layout değişimi hareket sırasında doğrudan uygulanmamalıdır. Authority state
machine değişikliği algıladığında controlled stop uygulamalı ve yeni layout'u
ancak seçili gaz/direksiyon eksenleri nötr kaldıktan sonra yeniden arm etmelidir.

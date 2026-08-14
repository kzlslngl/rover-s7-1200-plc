# Authority State Machine

Bu blok yalnız komut kaynağı yetkisi ve hareket inhibit durumu üretir. Motor,
fren, direksiyon, kontaktör veya başka bir fiziksel çıkış sürmez.

## Durumlar

| Kod | Durum | Açıklama |
|---:|---|---|
| 0 | SAFE | Aktif yetki yok |
| 1 | CONTROLLED_STOP | Kontrollü duruş tamamlanması bekleniyor |
| 2 | MANUAL_WAIT_NEUTRAL | G16 eksenleri nötrde bekleniyor |
| 3 | MANUAL_ACTIVE | G16 manuel yetkisi aktif |
| 4 | AUTO_WAIT_ORIN | Geçerli Orin komutu bekleniyor |
| 5 | AUTO_ACTIVE | Orin otomatik yetkisi aktif |
| 6 | FAULT | Safety chain veya iç durum hatası |

## TIA import ve bench çağrısı

Şu sırayla import et:

1. `exported/udt/UDT_AuthorityStatus.scl`
2. `exported/db/DB_AuthorityStatus.scl`
3. `exported/blocks/FB_AuthorityStateMachine.scl`

OB1 çağrısı:

```text
SafetyChainOk          := test_safety_ok
G16Valid               := DB_ValidatedG16Input.Data.Valid
G16Command             := DB_G16OperationalCommand.Data
OrinValid              := test_orin_valid
ControlledStopComplete := test_stop_complete
NeutralHoldTime        := T#500ms
AutoG16GraceTime       := T#2s
```

Gerçek safety ve controlled-stop bağlantıları hazır olmadığı için üç `test_*`
girişi yalnız watch table ile bench testi içindir ve production bağlantısı
değildir.

## Geçiş nedenleri

| Değer | Neden |
|---:|---|
| `16#0000` | normal/geçiş tamamlandı |
| `16#0001` | OperatorEnable kapandı |
| `16#0002` | controlled stop seçildi |
| `16#0003` | G16 geçersiz/kayıp |
| `16#0004` | Orin geçersiz/kayıp |
| `16#0005` | kontrol layout'u değişti |
| `16#0006` | safety chain uygun değil |
| `16#0007` | AUTO G16 grace süresi doldu |
| `16#0008` | authority kaynağı değişti |

MANUAL sırasında G16 kaybı beklemeden controlled stop üretir. AUTO sırasında
Orin validity sürekli zorunludur; G16 kaybı yalnız `AutoG16GraceTime` boyunca
toleranslıdır. G16 bu sürede geri gelirse ve MOD/SW1 hâlâ AUTO isterse AUTO
devam eder.

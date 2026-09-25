# GreenPulse — Sunum Paketi

**78 slayt · 1920×1080 · 16:9 · Türkçe**

```bash
python -m scripts.build_prez
```

Tüm sayılar `reports/` altındaki rapor dosyalarından **okunur**.
Üretici betikte elle yazılmış tek bir metrik yoktur; rapor değişirse
slayt da değişir.

---

## En önemli kural

> **Metrik ve donanım sonucu uydurulmaz.**

Projedeki katman raporlarının çoğu şu durumdadır:

```
SOFTWARE_..._FRAMEWORK_COMPLETE_REAL_..._PENDING
```

Yazılım hazır, **gerçek ölçüm yok**. Hailo, Raspberry Pi gecikmesi,
RAM/CPU/sıcaklık, uzun süre kararlılığı, gerçek sulama ve su tasarrufu
için projede **tek bir ölçülmüş sayı bulunmuyor**.

Bu slaytlar boş eksen veya örnek rakamla **doldurulmadı**. Ölçüm
protokolünü gösterir ve *"ölçülmedi"* der.

---

## Kanıt seviyesi rozetleri

Her slaytın sağ üst köşesinde bir rozet vardır. Jüri hiçbir grafiğin
kaynağını tahmin etmek zorunda kalmaz.

| Rozet | Anlamı | Slayt |
|---|---|---|
| **ÖLÇÜLDÜ** | Gerçek çalıştırma sonucu, rapor dosyasında kayıtlı | **15** |
| **YAZILIM DOĞRULANDI** | Kod ve test var; gerçek donanım/saha verisi yok | **37** |
| **TAHMİN** | Yöntemi belgelenmiş hesaplama — ölçüm değil | **1** |
| **GERÇEK TEST BEKLİYOR** | Henüz sayı yok — yalnızca ölçüm protokolü | **25** |

`prez_manifest.json` her slaytın rozetini, **veri kaynağını** ve
**ne iddia ettiğini** tek tek listeler.

---

## Bölümler

| Slayt | Bölüm | Ağırlıklı seviye |
|---|---|---|
| 01–04 | Giriş ve mimari | yazılım |
| 05–12 | Model performansı | **ölçüldü** |
| 13–16 | Veri bütünlüğü ve sızıntı kontrolü | **ölçüldü** |
| 17–28 | Füzyon, risk ve zamansal zekâ | yazılım |
| 29–36 | Güvenlik ve karar | yazılım |
| 37–45 | Donanım ve kapalı döngü | **bekliyor** |
| 46–56 | Uç birim başarımı | **bekliyor** |
| 57–67 | Arayüz ve sürdürülebilirlik | karışık |
| 68–78 | Mühendislik kanıtı | yazılım + ölçüldü |

---

## 5 dakikalık anlatı

Zaman kısıtlıysa bu sırayı kullanın:

| # | Slayt | Neden |
|---|---|---|
| 1 | `01_giris` | Problem ve akış |
| 2 | `05_performans_karnesi` | Ölçülmüş sonuç, tek ekranda |
| 3 | `06_domates_karisiklik_matrisi` | Sadece doğruluk değil, hata yapısı |
| 4 | `14_veri_bolmesi` | Test model seçimine katılmadı |
| 5 | `15_onnx_paritesi` | Uç birim hazırlığı ölçüldü |
| 6 | `30_guvenli_durum_matrisi` | Hata durumunda ne oluyor |
| 7 | `74_kanit_panosu` | Ne ölçüldü, ne bekliyor |
| 8 | `78_neden_greenpulse` | Kapanış |

**Jüri "peki donanım?" derse:** `43_hailo_dagitim_hatti` ve
`76_dogrulama_yol_haritasi`. İkisi de neyin ölçülmediğini açıkça söyler.

---

## Sık gelen itirazlar ve hangi slayt cevaplar

| İtiraz | Slayt |
|---|---|
| *"%99 doğruluk gerçekçi değil"* | `06`, `24` — hata yapısı ve en zayıf sınıf |
| *"Test setini ayarlama için kullandınız mı?"* | `14` — CONSUMED disiplini |
| *"Sızıntı var mı?"* | `13` — SHA + yaprak grubu + algısal karma |
| *"Grad-CAM lezyonu mu buluyor?"* | `08`, `09` — niteliksel tanılama |
| *"Transfer öğrenme işe yaradı mı?"* | `16` — **kanıtlanmadı**, iddia edilmiyor |
| *"Hailo hazır mı?"* | `43`, `44`, `45` — **hayır**, protokol hazır |
| *"Su tasarrufu ne kadar?"* | `61`, `62` — **ölçülmedi**, sayı verilmiyor |
| *"Sistem kendini sağlıklı mı sanıyor?"* | `56` — hayır, DEGRADED diyor |

---

## Dosya düzeni

```
prez/
├── README.md              bu dosya
├── prez_manifest.json     slayt → rozet · kaynak · iddia
└── slides/                78 PNG (1920×1080)
```

Üretici betikler:

| Dosya | Görev |
|---|---|
| `scripts/prez_design.py` | tasarım sistemi (renk, tipografi, bileşenler) |
| `scripts/build_prez.py` | veri katmanı + orkestrasyon + manifest |
| `scripts/prez_parts_a.py` | slayt 01–28 |
| `scripts/prez_parts_b.py` | slayt 29–78 |

---

## Bir ölçüm tamamlandığında

1. Ölçümü çalıştırın; sonucu `reports/` altına yazın
2. İlgili slaydın `tier` değerini `PENDING` → `MEASURED` yapın
3. `python -m scripts.build_prez`

Rozet, alt yazı ve manifest otomatik güncellenir.

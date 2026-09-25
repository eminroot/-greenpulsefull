# GreenPulse — AI/ML Paketi

**Biyo-Sinyal Analizli Proaktif Otonom Sera Sistemi**
TEKNOFEST 2026 · Tarım Teknolojileri

> Bu depo **operasyon öncesi** bir yazılım paketidir. Tamamlanmış bir
> Hailo dağıtımının, Raspberry Pi 5 + AI HAT+ doğrulamasının, fiziksel
> eyleme doğrulamasının veya gerçek sera doğrulamasının kanıtı **değildir**.

---

## Durum — tek bakışta

| | |
|---|---|
| Testler | **632 geçiyor**, 0 hata |
| Kapsam | Domates + Biber, bilgisayar tarafı hastalık sınıflandırması |
| Domates | doğruluk **%99,16** · Makro F1 **0,9899** · 2.737 görüntü · 23 hata |
| Biber | doğruluk **%98,11** · Makro F1 **0,9802** · 371 görüntü · 7 hata |
| ONNX eşitliği | 50 örnek, **0 sınıf uyuşmazlığı** |
| 56 katman | 10 tamam · 28 kısmi · 10 yazılım · 8 donanım bekliyor |
| Dağıtım | `RESEARCH_ONLY` — fiziksel eyleme **DEVRE DIŞI** |

**Bu sayılar gerçek sera doğruluğu değildir.** Sızıntı denetiminden
geçirilmiş, ayrılmış bir veri kümesi ölçütüdür.

---

## 30 saniyede çalıştırma

```bash
powershell -ExecutionPolicy Bypass -File release/install.ps1
```

```bash
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

```bash
powershell -ExecutionPolicy Bypass -File release/start.ps1
```

---

## Klasör haritası

| Klasör | İçerik |
|---|---|
| `src/` | 94 modül — çıkarım, füzyon, karar, kayıt defteri, denetim |
| `tests/` | 59 dosya, **632 test** |
| `scripts/` | eğitim, değerlendirme, dışa aktarma ve **üretim betikleri** |
| `models/` | domates + biber, `.pt` ve `.onnx` |
| `reports/` | 99 ölçüm raporu — görsellerin veri kaynağı |
| `jury_evidence/` | sunum materyali (aşağıya bakınız) |
| `release/` | teslim paketi, OpenAPI, şemalar, kurulum betikleri |
| `handoff/` | mühendislik teslim anlık görüntüsü + SHA manifesti |
| `datasets/` | eğitim verisi (4,9 GB) |

---

## Jüri sunumu

**Türkçe görseller:** `jury_evidence/visuals_tr/` — 12 slayt, 1920×1080

```bash
python -m scripts.build_jury_visuals_tr
```

Tüm sayılar `reports/` altındaki raporlardan **okunur**; bu betikte elle
yazılmış metrik yoktur. Rapor değişirse görsel de değişir.

**Savunma metni:** `reports/jury_final_shortlist_v1/ai_ml_defense_pack.md`
— 7 slayt için açılış cümlesi, teknik cümle, olası itiraz, cevap ve
*"asla söyleme"* listesi.

**Kanıt haritası:** `reports/greenpulse_jury_evidence_map_v1.md`
— 12 aşamalık anlatı, her aşamada konuşmacı cümlesi.

> Sunum dili **Türkçedir**. Önceki sürümde metinler Azerice yazılmış,
> ancak dosyalar cp1252/ASCII bir akışa yazıldığı için tüm özel harfler
> `?` karakterine dönüşmüştü (1.384 karakter). Kayıplı bozulma geri
> getirilemediği için metin tahmin edilerek onarılmadı; Türkçe yeniden
> yazıldı.

---

## Bakım betikleri

| Betik | Ne yapar |
|---|---|
| `scripts/build_jury_visuals_tr.py` | 12 Türkçe jüri görselini üretir |
| `scripts/rebuild_jury_defense_pack_tr.py` | Savunma paketini JSON'dan üretir |
| `scripts/repair_jury_text_encoding.py` | Bozuk karakterleri onarır |
| `scripts/sync_engineering_handoff.py` | Teslim paketini eşitler + SHA manifesti |

Teslim paketinin güncel olup olmadığını **dosyaya dokunmadan** kontrol
etmek için:

```bash
python -m scripts.sync_engineering_handoff --check
```

---

## Açık engeller — operasyonel sürüm bunları bekliyor

1. Hailo HEF dönüşümü ve eşitlik doğrulaması
2. Raspberry Pi 5 + AI HAT+ çalışma zamanı ölçümü
3. Gerçek sera görüntüsü ve alan kayması ölçümü
4. Kalibre edilmiş su stresi modeli
5. Pompa kalibrasyonu ve fiziksel kapalı döngü
6. Nihai Git/GitHub sürüm kaydı

Ayrıntı: `jury_evidence/real_measurements/` — ölçüm protokolü ve
şablonlar hazırdır.

---

## İlke

Bu pakette **ölçülmemiş hiçbir şey iddia edilmez.**

Transfer öğrenmenin üstünlüğü doğrulamada görülmedi — **iddia
edilmiyor**. Grad-CAM niteliksel bir tanılamadır — lezyon bölütleme
**iddia edilmiyor**. ONNX eşitliği dışa aktarma tutarlılığını kanıtlar —
Hailo çalışma zamanı **iddia edilmiyor**.

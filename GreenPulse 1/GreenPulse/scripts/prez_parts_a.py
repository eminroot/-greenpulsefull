"""
GreenPulse sunum paketi - BOLUM A (slayt 01-28)

    01-04  Giris ve mimari
    05-12  Model performansi        (OLCULDU)
    13-16  Veri butunlugu           (OLCULDU)
    17-28  Fuzyon ve zeka katmani   (cogunlukla YAZILIM DOGRULANDI)

Kural: `PENDING` rozetli slaytta sayi gosterilmez.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import numpy as np

from scripts import prez_design as D
from scripts.build_prez import short

SRC_T = "reports/tomato_final_test_v1.json"
SRC_P = "reports/pepper_final_test_v1/final_test_report.json"


# --- 01-04  Giris ve mimari ------------------------------------------------

def s01(d, out, reg):
    fig = D.slide("GreenPulse", "Biyo-sinyal analizli proaktif otonom sera "
                  "sistemi", D.SOFTWARE, kicker="TEKNOFEST 2026 · Tarım Teknolojileri")
    D.flow(fig, [("Gör", D.BRAND), ("Anla", D.BRAND), ("Öngör", D.ACCENT),
                 ("Karar ver", D.ACCENT), ("Sula", D.WARN),
                 ("Doğrula", D.NEUTRAL)], y=0.50, h=0.155)
    D.bullets(fig, D.ML, 0.385, [
        "Bitki tek bir karede bozulmaz — görüntü, sensör ve zaman birlikte okunur",
        "Her karar açıklanabilir gerekçe kodlarıyla kayda geçer",
        "Fiziksel eyleme güvenlik kapısının arkasındadır",
    ], size=D.T_BODY + 1)
    D.foot(fig, "Mevcut doğrulanmış kapsam: domates + biber, bilgisayar "
                "tarafı hastalık sınıflandırması. Fiziksel eyleme DEVRE DIŞI.")
    D.save(fig, out, "01_giris.png", reg, tier=D.SOFTWARE,
           source="reports/greenpulse_56_layer_master_status_v1.json",
           claim="Sistem kapsamı ve akış tanımı")


def s02(d, out, reg):
    fig = D.slide("Uçtan Uca Sistem Mimarisi",
                  "Tek model değil; birbirinden ayrılmış karar katmanları",
                  D.SOFTWARE, kicker="Mimari")
    rows = [
        ("ALGILAMA", ["ESP32-CAM görüntü", "Toprak nemi", "Sıcaklık / nem"], D.ACCENT),
        ("ANLAMA", ["Kalite kapısı", "Hastalık sınıflandırma", "Sensör doğrulama"], D.BRAND),
        ("ZEKÂ", ["Çok modlu füzyon", "Risk skoru", "Zamansal doğrulama"], D.WARN),
        ("KARAR", ["Güvenlik politikası", "Gerekçe kodları", "İnsan incelemesi"], D.ALERT),
    ]
    y0, rh = 0.70, 0.155
    for i, (band, items, col) in enumerate(rows):
        y = y0 - i * rh
        fig.text(D.ML, y + 0.048, band, fontsize=D.T_SMALL, fontweight="bold",
                 color=col)
        for j, it in enumerate(items):
            x = D.ML + 0.115 + j * 0.285
            D.panel(fig, x, y, 0.265, 0.095, ec=col, lw=1.6)
            fig.text(x + 0.132, y + 0.047, it, fontsize=D.T_BODY - 1,
                     color=D.INK, ha="center", va="center", zorder=2)
    D.foot(fig, "Model kayıt defteri, denetim günlüğü ve aktif öğrenme "
                "kuyruğu tüm katmanlara diktir.")
    D.save(fig, out, "02_sistem_mimarisi.png", reg, tier=D.SOFTWARE,
           source="src/ (94 modül) + reports/layer*.json",
           claim="Katman ayrımı ve veri akışı")


def s03(d, out, reg):
    fig = D.slide("Risk Tabanlı Otomatik Sulama Hattı",
                  "Görüntü ve sensör kanıtı tek bir risk skoruna indirgenir",
                  D.SOFTWARE, kicker="Karar hattı")
    D.flow(fig, [("Kare\nyakala", D.ACCENT), ("Kalite\nkapısı", D.ACCENT),
                 ("Hastalık\nsınıfı", D.BRAND), ("Sensör\ndoğrulama", D.BRAND),
                 ("Füzyon", D.WARN), ("Risk\n0–100", D.WARN),
                 ("Güvenlik\nkapısı", D.ALERT), ("Sulama\nisteği", D.ALERT)],
           y=0.52, h=0.165)
    bands = [("0–24", "İŞLEM YOK", D.BRAND), ("25–49", "İZLE", D.ACCENT),
             ("50–74", "UYARI", D.WARN), ("75–100", "SULAMA İSTEĞİ", D.ALERT)]
    for i, (rng, act, col) in enumerate(bands):
        x = D.ML + i * 0.228
        D.panel(fig, x, 0.20, 0.21, 0.145, ec=col, lw=1.8)
        fig.text(x + 0.105, 0.295, rng, fontsize=D.T_H2, fontweight="bold",
                 color=col, ha="center", zorder=2)
        fig.text(x + 0.105, 0.240, act, fontsize=D.T_SMALL, color=D.MUTED,
                 ha="center", zorder=2)
    D.foot(fig, "Eşikler yazılımda kalibre edildi; gerçek sera verisiyle "
                "yeniden kalibrasyon bekliyor.")
    D.save(fig, out, "03_risk_tabanli_sulama_hatti.png", reg, tier=D.SOFTWARE,
           source="reports/layer26_*.json, reports/layer27_*.json",
           claim="Risk bantları ve eylem eşlemesi")


def s04(d, out, reg):
    fig = D.slide("Kapalı Döngü Sulama Çevrimi",
                  "Müdahale sonrası etki ölçülür; döngü kendini doğrular",
                  D.SOFTWARE, kicker="Kapalı döngü")
    cx, cy, r = 0.50, 0.44, 0.215
    steps = ["Risk\nyükselir", "Sulama\nisteği", "Güvenlik\nonayı",
             "Pompa\nçalışır", "ACK\nalınır", "Sensör\ndeğişimi",
             "Risk\ndüşer", "Kayıt +\ndenetim"]
    n = len(steps)
    for i, label in enumerate(steps):
        ang = np.pi / 2 - 2 * np.pi * i / n
        x = cx + r * np.cos(ang) * (D.H / D.W) * 1.75
        y = cy + r * np.sin(ang)
        col = D.SEQ[i % len(D.SEQ)]
        D.panel(fig, x - 0.072, y - 0.048, 0.144, 0.096, ec=col, lw=1.8)
        fig.text(x, y, label, fontsize=D.T_SMALL, fontweight="bold",
                 color=col, ha="center", va="center", zorder=2,
                 linespacing=1.3)
    fig.text(cx, cy, "KAPALI\nDÖNGÜ", fontsize=D.T_H2, fontweight="bold",
             color=D.FAINT, ha="center", va="center", linespacing=1.3)
    D.foot(fig, "Döngünün yazılım tarafı test edilmiştir; gerçek pompa ve "
                "sensör tepkisi ölçülmemiştir.", D.ALERT)
    D.save(fig, out, "04_kapali_dongu_cevrimi.png", reg, tier=D.SOFTWARE,
           source="reports/layer40_closed_loop_feedback_intelligence_v1.json",
           claim="Kapalı döngü adımları (yazılım)")


# --- 05-12  Model performansi ---------------------------------------------

def s05(d, out, reg):
    t, p = d.t_metrics, d.p_metrics
    ev = d.t_eval
    fig = D.slide("Final Yapay Zekâ Performans Karnesi",
                  "Domates + biber, dondurulmuş nihai test", D.MEASURED,
                  kicker="Ölçülmüş sonuç")
    D.kpi_row(fig, [
        ("Domates doğruluk", D.tr_pct(t.get("accuracy", 0)),
         f"{D.tr_int(d.n(ev, 'images', 'total_images'))} görüntü", D.BRAND),
        ("Domates Makro F1", D.tr_num(t.get("macro_f1", 0)),
         "10 sınıf", D.BRAND),
        ("Biber doğruluk", D.tr_pct(p.get("accuracy", 0)),
         f"{d.pepper.get('evaluated_images', 0)} görüntü", D.ACCENT),
        ("Biber Makro F1", D.tr_num(p.get("macro_f1", 0)),
         "2 sınıf", D.ACCENT),
    ], y=0.485, h=0.250)
    D.kpi_row(fig, [
        ("Domates hata", str(d.n(ev, "errors")), "toplam", D.ALERT),
        ("Biber hata", str((d.pepper.get("error_analysis") or {})
                           .get("total_errors", 0)), "toplam", D.ALERT),
        ("ONNX uyuşmazlığı", str(d.onnx.get("class_mismatches", 0)),
         f"{d.onnx.get('parity_samples', 0)} örnekte", D.BRAND),
        ("Test kullanımı", "1 kez", "sonra CONSUMED", D.NEUTRAL, 28),
    ], y=0.185, h=0.250)
    D.foot(fig, "Bu sonuç gerçek sera doğruluğu DEĞİLDİR; sızıntı "
                "denetiminden geçirilmiş ayrılmış veri kümesi ölçütüdür.")
    D.save(fig, out, "05_performans_karnesi.png", reg, tier=D.MEASURED,
           source=f"{SRC_T}, {SRC_P}", claim="Dondurulmuş test metrikleri")


def _confusion(fig, ax, labels, matrix, *, annotate_all=True):
    m = np.array(matrix, dtype=float)
    norm = m / np.clip(m.sum(axis=1, keepdims=True), 1, None)
    im = ax.imshow(norm, cmap="Greens", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=38, ha="right",
                  fontsize=D.T_MICRO)
    ax.set_yticks(range(len(labels)), labels, fontsize=D.T_MICRO)
    ax.grid(False)
    for i in range(len(labels)):
        for j in range(len(labels)):
            v = int(m[i, j])
            if v == 0 and not annotate_all:
                continue
            ax.text(j, i, str(v), ha="center", va="center",
                    fontsize=D.T_MICRO,
                    color="white" if norm[i, j] > 0.55 else D.MUTED,
                    fontweight="bold" if i == j else "normal")
    ax.set_xlabel("tahmin", fontsize=D.T_SMALL, color=D.MUTED)
    ax.set_ylabel("gerçek", fontsize=D.T_SMALL, color=D.MUTED)
    return im


def s06(d, out, reg):
    order, matrix = d.t_confusion
    fig = D.slide("Domates — Karışıklık Matrisi",
                  "Köşegen doğru, köşegen dışı hata; sayılar mutlak",
                  D.MEASURED, kicker="Ölçülmüş sonuç")
    ax = fig.add_axes([0.335, 0.155, 0.40, 0.575])
    ax.set_facecolor(D.BG)
    _confusion(fig, ax, [short(c) for c in order], matrix)
    D.foot(fig, f"{D.tr_int(d.n(d.t_eval, 'images'))} görüntü · "
                f"{d.n(d.t_eval, 'errors')} hata · doğruluk "
                f"{D.tr_pct(d.t_metrics.get('accuracy', 0))}")
    D.save(fig, out, "06_domates_karisiklik_matrisi.png", reg,
           tier=D.MEASURED, source=SRC_T, claim="Sınıf düzeyinde hata yapısı")


def s07(d, out, reg):
    order, matrix = d.p_confusion
    fig = D.slide("Biber — Karışıklık Matrisi",
                  "İki sınıf; tüm hatalar tek yönde", D.MEASURED,
                  kicker="Ölçülmüş sonuç")
    ax = fig.add_axes([0.37, 0.24, 0.26, 0.46])
    ax.set_facecolor(D.BG)
    _confusion(fig, ax, [c.replace("_", " ") for c in order], matrix)
    err = (d.pepper.get("error_analysis") or {})
    D.foot(fig, f"{d.pepper.get('evaluated_images', 0)} görüntü · "
                f"{err.get('total_errors', 0)} hata · "
                f"{err.get('leaf_groups_with_errors', 0)} yaprak grubunda · "
                f"doğruluk {D.tr_pct(d.p_metrics.get('accuracy', 0))}")
    D.save(fig, out, "07_biber_karisiklik_matrisi.png", reg,
           tier=D.MEASURED, source=SRC_P, claim="İki sınıflı hata yapısı")


def _gradcam(d, out, reg, crop, folder, fname, title):
    import matplotlib.image as mpimg

    base = Path(folder)
    cands = sorted(base.glob("*/gradcam_overlay.png"))
    fig = D.slide(title, "Orijinal · ısı haritası · bindirme — niteliksel "
                  "dikkat tanılaması", D.MEASURED, kicker="Açıklanabilirlik")
    if not cands:
        D.pending_note(fig, "Grad-CAM çıktısı bulunamadı.")
        D.save(fig, out, fname, reg, tier=D.PENDING, source=folder,
               claim="Grad-CAM görseli üretilmemiş")
        return
    sample = cands[0].parent
    names = [("original.png", "Orijinal"), ("gradcam_heatmap.png", "Isı haritası"),
             ("gradcam_overlay.png", "Bindirme")]
    for i, (f, lbl) in enumerate(names):
        p = sample / f
        ax = fig.add_axes([0.075 + i * 0.295, 0.20, 0.26, 0.50])
        ax.axis("off")
        if p.exists():
            ax.imshow(mpimg.imread(p))
        else:
            ax.text(0.5, 0.5, "—", fontsize=40, color=D.FAINT,
                    ha="center", va="center")
        ax.set_title(lbl, fontsize=D.T_BODY, color=D.INK, pad=10)
    fig.text(D.ML, 0.135, f"Sınıf: {sample.name.replace('_', ' ')}",
             fontsize=D.T_SMALL, color=D.MUTED)
    D.foot(fig, "Grad-CAM yalnızca dikkat tanılamasıdır. Piksel düzeyinde "
                "lezyon bölütleme veya nedensellik İDDİA EDİLMEZ.")
    D.save(fig, out, fname, reg, tier=D.MEASURED, source=folder,
           claim=f"{crop} Grad-CAM görselleri")


def s08(d, out, reg):
    _gradcam(d, out, reg, "Domates", "reports/tomato_explainability_v1",
             "08_domates_gradcam.png", "Domates — Grad-CAM")


def s09(d, out, reg):
    _gradcam(d, out, reg, "Biber", "reports/pepper_explainability_v1",
             "09_biber_gradcam.png", "Biber — Grad-CAM")


def _curve_rows(d, rel):
    rows = d.curve(rel)
    def col(*names):
        for n in names:
            if rows and n in rows[0]:
                return n
        return None
    return rows, col


def s10(d, out, reg):
    rows, col = _curve_rows(d, "runs/greenpulse/tomato_cpu_v1/results.csv")
    fig = D.slide("Domates — Eğitim ve Doğrulama Eğrisi",
                  "Model seçimi yalnızca doğrulama sonuçlarına dayandı",
                  D.MEASURED, kicker="Eğitim kanıtı")
    if not rows:
        D.pending_note(fig, "Eğitim eğrisi dosyası bulunamadı.")
        D.save(fig, out, "10_domates_egitim_egrisi.png", reg, tier=D.PENDING,
               source="runs/greenpulse/tomato_cpu_v1/results.csv",
               claim="Eğitim eğrisi yok")
        return
    e = col("epoch")
    loss = col("train/loss", "train/cls_loss")
    vloss = col("val/loss", "val/cls_loss")
    acc = col("metrics/accuracy_top1")
    ax = D.ax_area(fig, 0.075, 0.20, 0.40, 0.52)
    xs = [float(r[e]) for r in rows]
    if loss:
        ax.plot(xs, [float(r[loss]) for r in rows], color=D.ACCENT, lw=2.4,
                label="eğitim kaybı")
    if vloss:
        ax.plot(xs, [float(r[vloss]) for r in rows], color=D.ALERT, lw=2.4,
                ls="--", label="doğrulama kaybı")
    ax.set_xlabel("epoch", fontsize=D.T_SMALL, color=D.MUTED)
    ax.legend(frameon=False, fontsize=D.T_SMALL)
    ax.set_title("Kayıp", fontsize=D.T_BODY, color=D.INK, loc="left")

    ax2 = D.ax_area(fig, 0.545, 0.20, 0.40, 0.52)
    if acc:
        ax2.plot(xs, [float(r[acc]) * 100 for r in rows], color=D.BRAND,
                 lw=2.6)
        ax2.set_ylim(min(80, min(float(r[acc]) * 100 for r in rows) - 2), 101)
    ax2.set_xlabel("epoch", fontsize=D.T_SMALL, color=D.MUTED)
    ax2.set_title("Doğrulama doğruluğu (%)", fontsize=D.T_BODY, color=D.INK,
                  loc="left")
    D.foot(fig, f"{len(rows)} epoch · CPU · genel ön eğitimli temelden "
                "temiz deney (önceki domates kontrol noktası kullanılmadı)")
    D.save(fig, out, "10_domates_egitim_egrisi.png", reg, tier=D.MEASURED,
           source="runs/greenpulse/tomato_cpu_v1/results.csv",
           claim="Eğitim / doğrulama eğrisi")


def s11(d, out, reg):
    pairs = d.tomato.get("top_error_pairs", [])
    fig = D.slide("Domates — Hata Çifti Analizi",
                  "Model nerede yanılıyor: en sık karışan sınıf çiftleri",
                  D.MEASURED, kicker="Hata yapısı")
    if not pairs:
        D.pending_note(fig, "Hata çifti verisi yok.")
        D.save(fig, out, "11_domates_hata_ciftleri.png", reg, tier=D.PENDING,
               source=SRC_T, claim="Hata çifti yok")
        return
    top = pairs[:8][::-1]
    ax = D.ax_area(fig, 0.34, 0.17, 0.60, 0.58)
    labels = [f"{short(p['true_class'])}  →  {short(p['predicted_class'])}"
              for p in top]
    vals = [p["count"] for p in top]
    ax.barh(labels, vals, color=D.ALERT, height=0.62, edgecolor="white")
    ax.grid(axis="x", alpha=0.28, linestyle=":", color=D.FAINT)
    ax.grid(axis="y", visible=False)
    for i, v in enumerate(vals):
        ax.text(v + 0.08, i, str(v), va="center", fontsize=D.T_SMALL,
                color=D.INK, fontweight="bold")
    ax.set_xlabel("hata sayısı", fontsize=D.T_SMALL, color=D.MUTED)
    ax.tick_params(axis="y", labelsize=D.T_MICRO)
    D.foot(fig, "Hata analizi yalnızca önceden kaydedilmiş tahmin "
                "dosyaları üzerinden yapıldı; test görüntülerine ikinci kez "
                "dokunulmadı.")
    D.save(fig, out, "11_domates_hata_ciftleri.png", reg, tier=D.MEASURED,
           source=SRC_T, claim="En sık karışan sınıf çiftleri")


def s12(d, out, reg):
    rows = d.predictions()
    fig = D.slide("Domates — Güven Dağılımı ve Hata Profili",
                  "Doğru ve yanlış tahminlerin güven dağılımı",
                  D.MEASURED, kicker="Güven analizi")
    if not rows:
        D.pending_note(fig, "Tahmin dosyası bulunamadı.")
        D.save(fig, out, "12_domates_guven_dagilimi.png", reg,
               tier=D.PENDING, source="reports/tomato_final_test_predictions_v1.csv",
               claim="Güven dağılımı yok")
        return
    ok = [float(r["confidence"]) for r in rows if r["correct"].lower() in ("true", "1")]
    bad = [float(r["confidence"]) for r in rows if r["correct"].lower() not in ("true", "1")]
    ax = D.ax_area(fig, 0.075, 0.20, 0.52, 0.53)
    bins = np.linspace(0, 1, 26)
    ax.hist(ok, bins=bins, color=D.BRAND, alpha=0.85, label=f"doğru ({len(ok)})")
    ax.hist(bad, bins=bins, color=D.ALERT, alpha=0.9, label=f"hata ({len(bad)})")
    ax.set_yscale("log")
    ax.set_xlabel("güven", fontsize=D.T_SMALL, color=D.MUTED)
    ax.set_ylabel("adet (log)", fontsize=D.T_SMALL, color=D.MUTED)
    ax.legend(frameon=False, fontsize=D.T_SMALL)
    hi = sum(1 for v in bad if v >= 0.90)
    D.kpi(fig, 0.645, 0.50, 0.30, 0.22, "Yüksek güvenli hata",
          str(hi), "güven ≥ 0,90 — en tehlikeli hata türü", D.ALERT)
    D.kpi(fig, 0.645, 0.22, 0.30, 0.22, "Ortalama güven (hata)",
          D.tr_num(float(np.mean(bad)) if bad else 0, 3),
          f"doğru tahminlerde {D.tr_num(float(np.mean(ok)) if ok else 0, 3)}",
          D.NEUTRAL)
    D.foot(fig, "Yüksek güvenli hatalar insan inceleme kuyruğunun öncelikli "
                "girdisidir.")
    D.save(fig, out, "12_domates_guven_dagilimi.png", reg, tier=D.MEASURED,
           source="reports/tomato_final_test_predictions_v1.csv",
           claim="Güven dağılımı ve yüksek güvenli hata sayısı")


# --- 13-16  Veri butunlugu -------------------------------------------------

def s13(d, out, reg):
    fig = D.slide("Veri Bütünlüğü ve Sızıntı Kontrolü",
                  "Metrikten önce veri kümesinin kendisi denetlendi",
                  D.MEASURED, kicker="Veri disiplini")
    D.flow(fig, [("Ham veri\ntoplama", D.NEUTRAL), ("SHA\nçakışma", D.ACCENT),
                 ("Yaprak grubu\nayrımı", D.BRAND), ("dHash / pHash\nyakın kopya", D.BRAND),
                 ("Bölme\nmanifesti", D.ACCENT), ("Dondurma\n(SHA)", D.ALERT)],
           y=0.50, h=0.16)
    D.bullets(fig, D.ML, 0.375, [
        "Tam SHA çakışması kontrol edildi",
        "Eşlenmiş domates alt kümesinde yaprak grubu ayrık bölme kuruldu",
        "Ek olarak algısal karma (dHash/pHash) ile yakın kopya taraması yapıldı",
    ])
    D.foot(fig, "Eşlenmemiş bölüm için fiziksel yaprak kimliği KANITLANMIŞ "
                "SAYILMAZ — bu sınır açıkça kayıt altındadır.", D.WARN)
    D.save(fig, out, "13_veri_butunlugu.png", reg, tier=D.MEASURED,
           source="reports/tomato_cross_split_near_duplicates_v1.csv, "
                  "reports/tomato_perceptual_hashes_v1.csv",
           claim="Sızıntı kontrol adımları")


def s14(d, out, reg):
    c = d.tomato_card.get("dataset", {})
    fig = D.slide("Eğitim / Doğrulama / Dondurulmuş Test Bölmesi",
                  "Nihai test, model seçimine hiç katılmadı", D.MEASURED,
                  kicker="Bölme")
    tr, va, te = (c.get("train_images", 0), c.get("validation_images", 0),
                  c.get("frozen_test_images", 0))
    total = max(tr + va + te, 1)
    x = D.ML
    for label, n, col in (("Eğitim", tr, D.BRAND), ("Doğrulama", va, D.ACCENT),
                          ("Dondurulmuş test", te, D.ALERT)):
        w = (D.MR - D.ML) * n / total
        D.panel(fig, x, 0.50, w, 0.14, ec=col, lw=2.0)
        fig.text(x + w / 2, 0.585, label, fontsize=D.T_BODY,
                 fontweight="bold", color=col, ha="center", zorder=2)
        fig.text(x + w / 2, 0.535, D.tr_int(n), fontsize=D.T_H2,
                 fontweight="bold", color=D.INK, ha="center", zorder=2)
        x += w
    D.kpi_row(fig, [
        ("Yaprak grubu çakışması", str(c.get("mapped_leaf_group_cross_split_overlap", 0)),
         "eşlenmiş alt küme", D.BRAND),
        ("Yakın kopya taraması", str(c.get("near_duplicate_screen", "—")),
         "dHash / pHash", D.BRAND, 26),
        ("Test kullanımı", "1 kez", "sonra CONSUMED", D.ALERT, 28),
        ("Test ile yeniden eğitim", "HAYIR", "politika gereği", D.ALERT, 26),
    ], y=0.20, h=0.21)
    D.foot(fig, "Toplam " + D.tr_int(total) + " görüntü · test açılmadan önce "
                "SHA ile donduruldu.")
    D.save(fig, out, "14_veri_bolmesi.png", reg, tier=D.MEASURED,
           source="reports/tomato_model_card_v1.json",
           claim="Bölme sayıları ve dondurma disiplini")


def s15(d, out, reg):
    o = d.onnx
    fig = D.slide("PyTorch → ONNX Eşitliği",
                  "Dışa aktarılan model, kaynak modelle aynı kararı veriyor mu?",
                  D.MEASURED, kicker="Uç birim hazırlığı")
    D.flow(fig, [("PyTorch\n.pt", D.NEUTRAL), ("ONNX\ndışa aktarım", D.ACCENT),
                 ("Örnek örnek\nkarşılaştırma", D.BRAND),
                 ("Top-1 eşitliği", D.BRAND)], y=0.52, h=0.155)
    D.kpi_row(fig, [
        ("Karşılaştırılan örnek", str(o.get("parity_samples", 0)), "doğrulama kümesi", D.NEUTRAL),
        ("Sınıf uyuşmazlığı", str(o.get("class_mismatches", 0)), "Top-1 tahmin", D.BRAND),
        ("Maks. olasılık farkı", f"{o.get('max_probability_absolute_difference', 0):.2e}",
         "mutlak", D.BRAND, 26),
        ("ONNX denetleyici", str(o.get("checker", "—")), "runtime: " + str(o.get("runtime", "—")),
         D.BRAND, 26),
    ], y=0.235, h=0.250)
    D.foot(fig, "ONNX eşitliği YALNIZCA dışa aktarma tutarlılığını kanıtlar. "
                "Hailo HEF dönüşümü ve donanım çalışma zamanı ayrıca "
                "beklemededir.", D.WARN)
    D.save(fig, out, "15_onnx_paritesi.png", reg, tier=D.MEASURED,
           source="reports/tomato_model_card_v1.json",
           claim="ONNX dışa aktarma eşitliği")


def s16(d, out, reg):
    c = d.pepper_cmp
    tm, bm = c.get("transfer_metrics", {}), c.get("baseline_metrics", {})
    fig = D.slide("Biber — Transfer Öğrenme vs Genel Temel Model",
                  "Üstünlük varsayılmadı; kontrollü karşılaştırma yapıldı",
                  D.MEASURED, kicker="Kontrollü deney")
    ax = D.ax_area(fig, 0.075, 0.22, 0.48, 0.50)
    keys = [("accuracy", "Doğruluk"), ("macro_f1", "Makro F1"),
            ("macro_precision", "Precision"), ("macro_recall", "Recall")]
    xs = np.arange(len(keys))
    ax.bar(xs - 0.19, [tm.get(k, 0) * 100 for k, _ in keys], 0.36,
           label="Domatesten transfer", color=D.BRAND, edgecolor="white")
    ax.bar(xs + 0.19, [bm.get(k, 0) * 100 for k, _ in keys], 0.36,
           label="Genel temel", color=D.NEUTRAL, edgecolor="white")
    ax.set_xticks(xs, [n for _, n in keys], fontsize=D.T_SMALL)
    ax.set_ylim(90, 104)
    ax.legend(frameon=False, fontsize=D.T_SMALL, loc="upper center",
              bbox_to_anchor=(0.5, 1.16), ncol=2)
    pr = c.get("paired_results", {})
    D.kpi(fig, 0.60, 0.50, 0.345, 0.22, "Gözlenen Makro F1 farkı",
          D.tr_num(c.get("observed_macro_f1_difference", 0), 4),
          f"{c.get('validation_images', 0)} doğrulama görüntüsü", D.NEUTRAL)
    D.kpi(fig, 0.60, 0.22, 0.345, 0.22, "Farklı tahmin",
          str(pr.get("different_predictions", 0)),
          "iki aday da aynı kararı verdi", D.NEUTRAL)
    D.foot(fig, f"Karşılaştırma yalnızca DOĞRULAMA kümesindedir "
                f"({c.get('comparison_split', '—')}). "
                "Transfer üstünlüğü KANITLANMADI — iddia edilmiyor.", D.WARN)
    D.save(fig, out, "16_biber_transfer_karsilastirma.png", reg,
           tier=D.MEASURED, source="reports/pepper_model_comparison_v1.json",
           claim="Transfer vs temel model karşılaştırması")


# --- 17-28  Fuzyon ve zeka -------------------------------------------------

def s17(d, out, reg):
    fig = D.slide("Çok Modlu Füzyon Mimarisi",
                  "Görüntü + sensör + bitki temel profili + zaman",
                  D.SOFTWARE, kicker="Füzyon")
    srcs = [("Görüntü\nkanıtı", D.BRAND), ("Sensör\nokuması", D.ACCENT),
            ("Bitki temel\nprofili", D.WARN), ("Zamansal\npencere", D.NEUTRAL)]
    for i, (label, col) in enumerate(srcs):
        x = D.ML + i * 0.232
        D.panel(fig, x, 0.60, 0.212, 0.125, ec=col, lw=1.9)
        fig.text(x + 0.106, 0.6625, label, fontsize=D.T_BODY - 1,
                 fontweight="bold", color=col, ha="center", va="center",
                 zorder=2, linespacing=1.3)
        fig.patches.append(mpatches.FancyArrow(
            x + 0.106, 0.592, 0.0, -0.052, width=0.0012,
            head_width=0.009, head_length=0.012,
            transform=fig.transFigure, fc=D.FAINT, ec="none"))
    D.panel(fig, 0.28, 0.42, 0.44, 0.105, ec=D.BRAND_DK, lw=2.2)
    fig.text(0.50, 0.4725, "ÖZELLİK FÜZYONU — sürümlenmiş şema",
             fontsize=D.T_BODY, fontweight="bold", color=D.BRAND_DK,
             ha="center", va="center", zorder=2)
    D.flow(fig, [("Risk skoru 0–100", D.WARN),
                 ("Zamansal doğrulama", D.ACCENT),
                 ("Güvenlik kapısı", D.ALERT)], y=0.25, h=0.105)
    D.foot(fig, "Füzyon için yazılım sözleşmesi ve testler mevcuttur. "
                "Gerçek senkronize sensör-kamera veri kümesi olmadığı için "
                "KALİBRE EDİLMİŞ füzyon iddia edilmez.", D.WARN)
    D.save(fig, out, "17_fuzyon_mimarisi.png", reg, tier=D.SOFTWARE,
           source="reports/layer22_*.json, reports/layer25_*.json",
           claim="Füzyon girdi şeması ve akışı")


def s18(d, out, reg):
    fig = D.slide("Risk Zekâsı — 0–100 Skoru",
                  "Tek bir sayı değil; bant + gerekçe + eylem",
                  D.SOFTWARE, kicker="Risk motoru")
    ax = fig.add_axes([0.075, 0.20, 0.36, 0.52], polar=True)
    ax.set_facecolor(D.BG)
    bands = [(0, 25, D.BRAND), (25, 50, D.ACCENT), (50, 75, D.WARN),
             (75, 100, D.ALERT)]
    for lo, hi, col in bands:
        th = np.linspace(np.pi * (1 - lo / 100), np.pi * (1 - hi / 100), 60)
        ax.fill_between(th, 0.72, 1.0, color=col, alpha=0.92)
    ax.set_thetamin(0); ax.set_thetamax(180)
    ax.set_yticks([]); ax.set_xticks([])
    ax.spines["polar"].set_visible(False)
    fig.text(0.255, 0.335, "0 – 100", fontsize=30, fontweight="bold",
             color=D.INK, ha="center")
    fig.text(0.255, 0.295, "risk skoru", fontsize=D.T_SMALL, color=D.MUTED,
             ha="center")
    rows = [("0–24", "İŞLEM YOK", "izleme sürer"),
            ("25–49", "İZLE", "örnekleme sıklaşır"),
            ("50–74", "UYARI", "insan bilgilendirilir"),
            ("75–100", "SULAMA İSTEĞİ", "güvenlik kapısına gider")]
    D.table(fig, 0.50, 0.66, 0.445,
            (["Bant", "Eylem", "Sonuç"], [0.0, 0.26, 0.58]), rows, rh=0.085,
            col_colors={1: D.ALERT})
    D.foot(fig, "Eşikler yazılımda kalibre edildi; gerçek sera verisiyle "
                "yeniden kalibrasyon bekliyor.", D.WARN)
    D.save(fig, out, "18_risk_skoru_gostergesi.png", reg, tier=D.SOFTWARE,
           source="reports/layer26_*.json, reports/layer27_*.json",
           claim="Risk bantları ve eylem eşlemesi")


def s19(d, out, reg):
    fig = D.slide("Sensör Kartları ve Geçerlilik Durumu",
                  "Her okuma geçerlilik damgasıyla birlikte taşınır",
                  D.SOFTWARE, kicker="Sensör sözleşmesi")
    cards = [("Toprak nemi", "%", "kritik eşik altı → risk katkısı", D.BRAND),
             ("Sıcaklık", "°C", "yüksek sıcaklık → buharlaşma", D.WARN),
             ("Bağıl nem", "%", "düşük nem → stres hızlanır", D.ACCENT),
             ("Geçerlilik", "VALID / STALE / MISSING / INVALID",
              "geçersiz okuma karara GİRMEZ", D.ALERT)]
    for i, (name, unit, note, col) in enumerate(cards):
        x = D.ML + i * 0.232
        D.panel(fig, x, 0.38, 0.212, 0.30, ec=col, lw=1.8)
        fig.text(x + 0.018, 0.645, name, fontsize=D.T_BODY,
                 fontweight="bold", color=D.INK, zorder=2)
        fig.text(x + 0.018, 0.555, unit, fontsize=D.T_H2 if len(unit) < 6 else D.T_SMALL,
                 fontweight="bold", color=col, zorder=2)
        fig.text(x + 0.018, 0.415, note, fontsize=D.T_MICRO, color=D.MUTED,
                 zorder=2, wrap=True)
    D.bullets(fig, D.ML, 0.315, [
        "Bayat (STALE) okuma karar üretmez — sistem izlemeye döner",
        "Eksik sensör, görüntü kanıtını tek başına yetkilendirmez",
    ])
    D.foot(fig, "Sensör sözleşmesi ve doğrulama testleri mevcuttur; gerçek "
                "sera sensör akışı henüz bağlanmamıştır.", D.WARN)
    D.save(fig, out, "19_sensor_kartlari.png", reg, tier=D.SOFTWARE,
           source="reports/layer20_sensor_feature_engineering_v1.json",
           claim="Sensör alanları ve geçerlilik durumları")


def _pending_slide(out, reg, fname, title, subtitle, kicker, protocol,
                   why, source):
    """Sayi olmayan PENDING slayti - protokol + neden."""
    fig = D.slide(title, subtitle, D.PENDING, kicker=kicker)
    # Panel yuksekligi ICERIGE gore hesaplanir; sabit yukseklik
    # slaytin alt yarisini bos birakiyordu.
    dy = 0.062
    rows = max(len(protocol), len(why))
    h = 0.115 + rows * dy
    top = 0.735
    y = top - h
    D.panel(fig, D.ML, y, 0.445, h, ec=D.ALERT, lw=1.8)
    fig.text(D.ML + 0.022, top - 0.042, "ÖLÇÜM PROTOKOLÜ HAZIR",
             fontsize=D.T_BODY, fontweight="bold", color=D.ALERT, zorder=2)
    D.bullets(fig, D.ML + 0.022, top - 0.098, protocol, size=D.T_SMALL,
              dy=dy, marker="•")
    D.panel(fig, 0.515, y, 0.433, h, ec=D.LINE, lw=1.4)
    fig.text(0.537, top - 0.042, "NEDEN SAYI YOK", fontsize=D.T_BODY,
             fontweight="bold", color=D.MUTED, zorder=2)
    D.bullets(fig, 0.537, top - 0.098, why, size=D.T_SMALL, dy=dy,
              color=D.MUTED, marker="•")
    fig.text(D.ML, y - 0.075, "Bu aşama tamamlandığında slayt ölçülmüş "
             "değerlerle yeniden üretilir.", fontsize=D.T_BODY,
             color=D.INK)
    D.pending_note(fig, "Gerçek ölçüm yapılmadan bu slayta rakam yazılmaz.")
    D.save(fig, out, fname, reg, tier=D.PENDING, source=source,
           claim="Ölçüm protokolü — sonuç yok")


def s20(d, out, reg):
    fig = D.slide("Risk Eğilim Zaman Çizgisi",
                  "Tek kare değil, pencere içindeki gidişat okunur",
                  D.SOFTWARE, kicker="Zamansal zekâ")
    ax = D.ax_area(fig, 0.075, 0.22, 0.60, 0.50)
    for lo, hi, col, lbl in ((0, 25, D.BRAND, "işlem yok"),
                             (25, 50, D.ACCENT, "izle"),
                             (50, 75, D.WARN, "uyarı"),
                             (75, 100, D.ALERT, "sulama isteği")):
        ax.axhspan(lo, hi, color=col, alpha=0.12)
        ax.text(0.2, (lo + hi) / 2, lbl, fontsize=D.T_MICRO, color=col,
                va="center")
    ax.set_ylim(0, 100)
    ax.set_xlim(0, 10)
    ax.set_xlabel("zaman (örnekleme penceresi)", fontsize=D.T_SMALL,
                  color=D.MUTED)
    ax.set_ylabel("risk skoru", fontsize=D.T_SMALL, color=D.MUTED)
    ax.set_xticks([])
    ax.text(5, 50, "gerçek seri ölçülmedi", fontsize=D.T_BODY,
            color=D.FAINT, ha="center", style="italic")
    D.bullets(fig, 0.70, 0.66, ["Eğilim yönü", "Değişim hızı",
                                "İvmelenme", "Ardışık doğrulama"],
              size=D.T_BODY, dy=0.062)
    D.foot(fig, "Bantlar ve mantık yazılımda tanımlıdır; grafikteki eğri "
                "GERÇEK VERİ DEĞİLDİR ve bu yüzden çizilmemiştir.", D.ALERT)
    D.save(fig, out, "20_risk_egilim_zaman_cizgisi.png", reg,
           tier=D.SOFTWARE,
           source="reports/layer28_temporal_intelligence_v1.json",
           claim="Risk bantları ve zamansal okuma mantığı")


def s21(d, out, reg):
    fig = D.slide("Zamansal Zekâ — Eğilim, Hız, İvme",
                  "Aynı risk skoru, farklı gidişat: karar farklı olur",
                  D.SOFTWARE, kicker="Zamansal zekâ")
    cases = [("Sabit", "risk sabit", "izlemeye devam", D.BRAND),
             ("Yükselen", "risk artıyor", "örnekleme sıklaşır", D.WARN),
             ("Hızlanan", "artış ivmeleniyor", "erken uyarı", D.ALERT),
             ("Düşen", "müdahale sonrası", "etki doğrulanır", D.ACCENT)]
    for i, (name, state, act, col) in enumerate(cases):
        x = D.ML + i * 0.232
        D.panel(fig, x, 0.34, 0.212, 0.34, ec=col, lw=1.8)
        ax = fig.add_axes([x + 0.022, 0.475, 0.168, 0.145])
        ax.set_facecolor(D.PANEL)
        xs = np.linspace(0, 1, 40)
        ys = {"Sabit": np.full_like(xs, 0.5),
              "Yükselen": 0.25 + 0.5 * xs,
              "Hızlanan": 0.2 + 0.7 * xs ** 2,
              "Düşen": 0.8 - 0.55 * xs}[name]
        ax.plot(xs, ys, color=col, lw=3)
        ax.set_ylim(0, 1); ax.axis("off")
        fig.text(x + 0.106, 0.442, name, fontsize=D.T_BODY,
                 fontweight="bold", color=col, ha="center", zorder=2)
        fig.text(x + 0.106, 0.402, state, fontsize=D.T_MICRO, color=D.MUTED,
                 ha="center", zorder=2)
        fig.text(x + 0.106, 0.365, act, fontsize=D.T_MICRO, color=D.INK,
                 ha="center", zorder=2)
    D.foot(fig, "Eğriler mantığı anlatır; ölçülmüş seri DEĞİLDİR.", D.WARN)
    D.save(fig, out, "21_zamansal_zeka.png", reg, tier=D.SOFTWARE,
           source="reports/layer28_temporal_intelligence_v1.json",
           claim="Eğilim/hız/ivme kavramları")


def s22(d, out, reg):
    f = D.load_json("reports/layer29_predictive_risk_forecasting_v1.json")
    fig = D.slide("Öngörücü Risk — Tahmin Ufku",
                  "Hafif bir regresyon modeli, saf temel modelle "
                  "karşılaştırılmak üzere kuruldu", D.SOFTWARE,
                  kicker="Öngörü")
    D.kpi_row(fig, [
        ("Model türü", "Ridge", f.get("model_type", "").split("_")[0].title()
         or "doğrusal", D.ACCENT, 26),
        ("Özellik sayısı", str(f.get("feature_count", 0)), "6 kaynaktan",
         D.ACCENT),
        ("Saf temel model", "var", "karşılaştırma zorunlu", D.NEUTRAL, 26),
        ("Gerçek değerlendirme", "BEKLİYOR", "saha verisi yok", D.ALERT, 22),
    ], y=0.500, h=0.250)
    D.bullets(fig, D.ML, 0.42, [
        "Tahmin, saf temel modeli yenmeden FAYDALI SAYILMAZ",
        "Belirsizlik bandı olmadan tahmin sunulmaz",
        "Ufuk uzadıkça belirsizlik genişler — bu açıkça gösterilir",
    ])
    D.foot(fig, "Öngörü çerçevesi yazılımda tamamlandı; gerçek tahmin "
                "doğrulaması BEKLİYOR. Bu slaytta tahmin doğruluğu "
                "gösterilmez.", D.ALERT)
    D.save(fig, out, "22_ongoru_ufku.png", reg, tier=D.SOFTWARE,
           source="reports/layer29_predictive_risk_forecasting_v1.json",
           claim="Öngörü çerçevesi ve guardrail'ler")


def s23(d, out, reg):
    _pending_slide(
        out, reg, "23_ablasyon_karsilastirma.png",
        "Sensör / Görüntü / Füzyon Karşılaştırması",
        "Üç yollu ablasyon: hangi bileşen ne kadar katkı sağlıyor?",
        "Ablasyon",
        ["Yalnızca sensör temel modeli",
         "Yalnızca görüntü temel modeli",
         "Görüntü + sensör füzyonu",
         "Aynı bölme, aynı metrikler, eşleştirilmiş karşılaştırma"],
        ["Gerçek senkronize sensör-kamera veri kümesi yok",
         "Üç yollu değerlendirme henüz çalıştırılmadı",
         "Katkı payı ölçülmeden üstünlük iddia edilemez"],
        "reports/layer51_ablation_study_v1.json")


def s24(d, out, reg):
    pc = d.t_per_class
    fig = D.slide("Sınıf Düzeyinde Precision / Recall / F1",
                  "Ortalama değil; her sınıf ayrı ayrı", D.MEASURED,
                  kicker="Ölçülmüş sonuç")
    names = list(pc)[:10]
    ax = D.ax_area(fig, 0.075, 0.24, 0.87, 0.48)
    xs = np.arange(len(names))
    for off, key, col, lbl in ((-0.26, "precision", D.ACCENT, "Precision"),
                               (0.0, "recall", D.WARN, "Recall"),
                               (0.26, "f1", D.BRAND, "F1")):
        ax.bar(xs + off, [pc[n].get(key, 0) for n in names], 0.25,
               color=col, label=lbl, edgecolor="white")
    ax.set_xticks(xs, [short(n) for n in names], rotation=28, ha="right",
                  fontsize=D.T_MICRO)
    ax.set_ylim(0.8, 1.02)
    ax.legend(frameon=False, fontsize=D.T_SMALL, ncol=3, loc="upper center",
              bbox_to_anchor=(0.5, 1.13))
    worst = min(names, key=lambda n: pc[n].get("f1", 1))
    D.foot(fig, f"En zayıf sınıf: {short(worst)} — F1 "
                f"{D.tr_num(pc[worst].get('f1', 0), 4)}. Makro F1 tüm "
                "sınıflara eşit ağırlık verir.")
    D.save(fig, out, "24_sinif_duzeyinde_metrikler.png", reg,
           tier=D.MEASURED, source=SRC_T,
           claim="Sınıf düzeyinde precision/recall/F1")


def s25(d, out, reg):
    _pending_slide(
        out, reg, "25_tek_kare_vs_zamansal.png",
        "Tek Kare vs Zamansal Doğrulama",
        "Ardışık doğrulama yanlış alarmı ne kadar azaltıyor?",
        "Zamansal doğrulama",
        ["Aynı sahnede tek kare kararı",
         "Aynı sahnede N ardışık kare doğrulaması",
         "Yanlış pozitif ve yanlış negatif oranları karşılaştırılır"],
        ["Gerçek sera zaman serisi yok",
         "Yanlış alarm azalması ölçülmedi",
         "Azalma oranı ölçülmeden sunulamaz"],
        "reports/layer28_temporal_intelligence_v1.json")


def s26(d, out, reg):
    _pending_slide(
        out, reg, "26_tahmin_vs_gercek.png",
        "Tahmin vs Gerçek vs Saf Temel Model",
        "Öngörü, saf temel modeli gerçekten yeniyor mu?",
        "Öngörü doğrulaması",
        ["Aynı ufukta tahmin ve gerçek risk karşılaştırılır",
         "Saf temel model (son değeri tekrarla) referans alınır",
         "Belirsizlik bandı birlikte çizilir"],
        ["Gerçek risk serisi henüz toplanmadı",
         "Tahmin doğruluğu ölçülmedi",
         "Temel modeli yenmeden fayda iddia edilmez"],
        "reports/layer29_predictive_risk_forecasting_v1.json")


def s27(d, out, reg):
    _pending_slide(
        out, reg, "27_tahmin_onde_gitme_suresi.png",
        "Tahmin Önde Gitme Süresi",
        "Sistem stresi, görünür hasardan ne kadar önce haber veriyor?",
        "Erken uyarı",
        ["Kontrollü kuruma denemesi (5–7 takvim günü)",
         "Görünür hasar anı bağımsız olarak işaretlenir",
         "Uyarı anı ile hasar anı arasındaki fark ölçülür"],
        ["Kontrollü bitki denemesi yapılmadı",
         "Erken uyarı süresi ölçülmedi",
         "Bu, projenin ana iddiası — tahminle sunulamaz"],
        "reports/layer29_predictive_risk_forecasting_v1.json")


def s28(d, out, reg):
    fig = D.slide("Belirsizlik ve Görüntü–Sensör Çelişkisi",
                  "Sistem emin değilse karar vermez", D.SOFTWARE,
                  kicker="Güvenli davranış")
    D.flow(fig, [("Görüntü\nkanıtı", D.BRAND), ("Sensör\nkanıtı", D.ACCENT),
                 ("Uyum\nkontrolü", D.WARN)], y=0.60, h=0.125, arrow=True)
    outs = [("UYUMLU", "karar üretilir", D.BRAND),
            ("ÇELİŞKİLİ", "insan incelemesi", D.ALERT),
            ("BELİRSİZ", "çekimser kalınır", D.WARN),
            ("EKSİK VERİ", "izlemeye dönülür", D.NEUTRAL)]
    for i, (name, act, col) in enumerate(outs):
        x = D.ML + i * 0.232
        D.panel(fig, x, 0.27, 0.212, 0.155, ec=col, lw=1.9)
        fig.text(x + 0.106, 0.382, name, fontsize=D.T_BODY,
                 fontweight="bold", color=col, ha="center", zorder=2)
        fig.text(x + 0.106, 0.320, act, fontsize=D.T_SMALL, color=D.MUTED,
                 ha="center", zorder=2)
    D.foot(fig, "Çekimser kalma (ABSTAIN) bir başarısızlık değil, "
                "tasarlanmış bir çıktıdır.")
    D.save(fig, out, "28_belirsizlik_ve_celiski.png", reg, tier=D.SOFTWARE,
           source="reports/layer31_vision_sensor_conflict_v1.json",
           claim="Çelişki ve belirsizlik çıktıları")


def build(d, out: Path, reg: list) -> None:
    for fn in (s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12,
               s13, s14, s15, s16, s17, s18, s19, s20, s21, s22, s23, s24,
               s25, s26, s27, s28):
        try:
            fn(d, out, reg)
            print(f"  {fn.__name__}  {reg[-1]['file']}")
        except Exception as exc:                        # noqa: BLE001
            print(f"  {fn.__name__}  HATA: {exc}")

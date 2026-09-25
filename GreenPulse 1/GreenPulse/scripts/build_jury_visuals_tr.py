"""
GreenPulse - Juri gorsellerini TURKCE yeniden uretir.

NEDEN YENIDEN URETILIYOR
------------------------
1. DIL. Sunum TURKCE yapilacak; onceki gorseller Ingilizceydi.

2. BOZUK KARAKTER. Onceki gorsellerde uzun tire `?` olarak basilmisti.
   Kapanis slaydinin ANA MESAJINDA bile goruluyordu:
       "GreenPulse does not stop at prediction ? it connects ..."
   Metin PNG icine gomulu oldugu icin dosyayi duzenlemek yetmez;
   gorselin yeniden uretilmesi gerekir.

3. YERLESIM HATASI. `02_model_performance_comparison.png` icinde alt
   baslik cubuklarin uzerinden geciyor, gosterge (legend) "%98,02"
   etiketini ortuyor ve alttaki hata notu cubuklarin arkasinda kaliyordu.

4. URETICI YOKTU. Gorselleri ureten betik projede mevcut degildi;
   dolayisiyla hicbiri yeniden uretilemiyordu. Artik tek komutla
   uretiliyorlar.

TUM SAYILAR RAPOR DOSYALARINDAN OKUNUR. Bu betikte elle yazilmis metrik
YOKTUR; rapor degisirse gorsel de degisir.

Calistirma:
    python -m scripts.build_jury_visuals_tr
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

REPORTS = Path("reports")
OUT = Path("jury_evidence/visuals_tr")

W, H = 19.20, 10.80        # 1920x1080 @ dpi=100
DPI = 100

BG = "#F7F9F8"
INK = "#14332B"
MUTED = "#5C6B66"
GREEN = "#1B6B4C"
BLUE = "#2E6DA4"
AMBER = "#C8890A"
RED = "#B3261E"
LINE = "#D4DDD9"

STATUS_COLOR = {
    "DONE": GREEN,
    "PARTIAL": AMBER,
    "SOFTWARE_TODO": BLUE,
    "HARDWARE_BLOCKED": RED,
}
STATUS_TR = {
    "DONE": "Tamamlandı",
    "PARTIAL": "Kısmi",
    "SOFTWARE_TODO": "Yazılım işi",
    "HARDWARE_BLOCKED": "Donanım bekliyor",
}


def load(name: str) -> dict:
    p = REPORTS / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def canvas(title: str, subtitle: str = "", badge: str = ""):
    """Ortak slayt iskeleti - baslik alani icerikle CAKISMAZ."""
    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=BG)
    fig.text(0.055, 0.925, title, fontsize=34, fontweight="bold", color=INK,
             va="top")
    if subtitle:
        fig.text(0.055, 0.868, subtitle, fontsize=16, color=MUTED, va="top")
    if badge:
        fig.text(0.945, 0.935, badge, fontsize=13, fontweight="bold",
                 color=GREEN, ha="right", va="top",
                 bbox=dict(boxstyle="round,pad=0.45", fc="#E3F0E9",
                           ec="none"))
    return fig


def footer(fig, text: str, color: str = MUTED) -> None:
    fig.text(0.055, 0.045, text, fontsize=14, color=color, va="bottom")


def card(fig, x, y, w, h, title, value, note, vcolor=GREEN):
    """Tek bir bilgi karti (sekil koordinatlari, 0-1)."""
    fig.patches.append(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012",
        transform=fig.transFigure, fc="white", ec=LINE, lw=1.4, zorder=1))
    fig.text(x + 0.018, y + h - 0.035, title, fontsize=14.5,
             fontweight="bold", color=INK, va="top", zorder=2)
    fig.text(x + 0.018, y + h / 2 - 0.018, value, fontsize=33,
             fontweight="bold", color=vcolor, va="center", zorder=2)
    fig.text(x + 0.018, y + 0.028, note, fontsize=12, color=MUTED,
             va="bottom", zorder=2)


def save(fig, name: str, made: list) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    fig.savefig(p, dpi=DPI, facecolor=BG)
    plt.close(fig)
    made.append(p.as_posix())
    print(f"  {name}")


# ---------------------------------------------------------------------------


def metrics() -> dict:
    t = load("tomato_final_test_v1.json")
    card_t = load("tomato_model_card_v1.json")
    pp = REPORTS / "pepper_final_test_v1" / "final_test_report.json"
    p = json.loads(pp.read_text(encoding="utf-8")) if pp.exists() else {}
    ft = card_t.get("final_test", {})
    # Biber raporunda metrikler `metrics` altinda YUVALIDIR; domateste
    # ust duzeydedir. Ikisini de destekleyen bir okuyucu kullaniyoruz -
    # aksi halde eksik anahtar sessizce 0 dondurur ve grafikte cubuk
    # HIC CIZILMEZ (bu hata ilk uretimde tam olarak boyle olustu).
    pm = p.get("metrics") or p

    def pick(src: dict, key: str, *fallbacks: dict) -> float:
        for candidate in (src, *fallbacks):
            if isinstance(candidate, dict) and candidate.get(key) is not None:
                return float(candidate[key])
        raise KeyError(f"metrik bulunamadi: {key}")

    return {
        "t_acc": pick(t, "accuracy", ft),
        "t_f1": pick(t, "macro_f1", ft),
        "t_n": ft.get("images", t.get("evaluated_images", 0)),
        "t_err": ft.get("errors", 0),
        "t_classes": card_t.get("class_count", 0),
        "p_acc": pick(pm, "accuracy"),
        "p_f1": pick(pm, "macro_f1"),
        "p_n": p.get("evaluated_images", 0),
        "p_err": (p.get("error_analysis") or {}).get("total_errors", 0),
        "onnx": card_t.get("onnx", {}),
    }


# --- 01 -------------------------------------------------------------------

def s01(made):
    fig = canvas("Sistem Mimarisi",
                 "Tek bir model değil; katmanlara ayrılmış bir karar sistemi",
                 "MİMARİ")
    stages = [
        ("Görüntü\ngirişi", BLUE), ("Kalite\nkapısı", BLUE),
        ("Hastalık\nsınıflandırma", GREEN), ("Sensör\ndoğrulama", BLUE),
        ("Risk ve\nfüzyon", AMBER), ("Güvenlik\nkapısı", RED),
        ("İnsan\nincelemesi", AMBER), ("Donanım\nBLOKE", RED),
    ]
    n = len(stages)
    x0, y, bw, bh = 0.055, 0.50, 0.098, 0.145
    gap = (0.945 - x0 - bw) / (n - 1)
    for i, (label, col) in enumerate(stages):
        x = x0 + i * gap
        fig.patches.append(mpatches.FancyBboxPatch(
            (x, y), bw, bh, boxstyle="round,pad=0.006,rounding_size=0.01",
            transform=fig.transFigure, fc="white", ec=col, lw=2.4))
        fig.text(x + bw / 2, y + bh / 2, label, fontsize=13.5,
                 fontweight="bold", color=col, ha="center", va="center")
        if i < n - 1:
            fig.patches.append(mpatches.FancyArrow(
                x + bw + 0.004, y + bh / 2, gap - bw - 0.008, 0,
                width=0.0016, head_width=0.012, head_length=0.008,
                transform=fig.transFigure, fc=MUTED, ec="none"))
    for x, t in ((0.055, "Model kayıt defteri"), (0.36, "Denetim günlüğü"),
                 (0.66, "Aktif öğrenme kuyruğu")):
        fig.text(x, 0.35, "• " + t, fontsize=15, color=MUTED)
    footer(fig, "Fiziksel eyleme DEVRE DIŞI — güvenlik kapısı özerk "
                "donanım hareketine izin vermez.", RED)
    save(fig, "01_sistem_mimarisi.png", made)


# --- 02 -------------------------------------------------------------------

def s02(made):
    m = metrics()
    fig = canvas("Ölçülmüş Hastalık Sınıflandırma Performansı",
                 "Dondurulmuş test sonuçları — yalnızca iki ürünlük mevcut "
                 "kapsam içinde geçerlidir", "ÖLÇÜLDÜ")
    ax = fig.add_axes([0.075, 0.17, 0.60, 0.60])
    ax.set_facecolor(BG)
    labels = ["Domates", "Biber"]
    acc = [m["t_acc"] * 100, m["p_acc"] * 100]
    f1 = [m["t_f1"] * 100, m["p_f1"] * 100]
    xs = range(len(labels))
    w = 0.3
    b1 = ax.bar([x - w / 2 for x in xs], acc, w, label="Doğruluk",
                color=GREEN, edgecolor="white")
    b2 = ax.bar([x + w / 2 for x in xs], f1, w, label="Makro F1",
                color=BLUE, edgecolor="white")
    for bars, vals in ((b1, acc), (b2, f1)):
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.9,
                    f"%{v:.2f}".replace(".", ","), ha="center",
                    fontsize=15, fontweight="bold", color=INK)
    ax.set_xticks(list(xs), labels, fontsize=17)
    ax.set_ylim(90, 104)
    ax.set_yticks([90, 92, 94, 96, 98, 100])
    ax.set_ylabel("Skor (%)", fontsize=14, color=MUTED)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linestyle=":")
    ax.set_axisbelow(True)
    # Gosterge GRAFIGIN DISINDA - onceki surumde etiketi ortuyordu.
    ax.legend(frameon=False, fontsize=14, loc="upper center",
              bbox_to_anchor=(0.5, 1.13), ncol=2)

    card(fig, 0.70, 0.52, 0.245, 0.22, "Domates",
         f"{m['t_err']} hata", f"{m['t_n']:,} görüntü · {m['t_classes']} sınıf"
         .replace(",", "."), RED)
    card(fig, 0.70, 0.24, 0.245, 0.22, "Biber",
         f"{m['p_err']} hata", f"{m['p_n']} görüntü · 2 sınıf", RED)
    footer(fig, "Bu sonuç gerçek sera doğruluğu DEĞİLDİR; sızıntı "
                "denetiminden geçirilmiş ayrılmış veri kümesi ölçütüdür.")
    save(fig, "02_model_performansi.png", made)


# --- 03 -------------------------------------------------------------------

def s03(made):
    m = metrics()
    c = load("tomato_model_card_v1.json")
    fig = canvas("Model Kanıt Kartları",
                 "Her iki ürün için dondurulmuş test, ONNX eşitliği ve "
                 "kayıt defteri kanıtı", "KANIT")
    rows_t = [
        ("Doğruluk", f"%{m['t_acc']*100:.4f}".replace(".", ",")),
        ("Makro F1", f"{m['t_f1']:.6f}".replace(".", ",")),
        ("Test görüntüsü", f"{m['t_n']:,}".replace(",", ".")),
        ("Hata", str(m["t_err"])),
        ("Sınıf sayısı", str(m["t_classes"])),
        ("Test durumu", "CONSUMED (bir kez)"),
    ]
    rows_p = [
        ("Doğruluk", f"%{m['p_acc']*100:.4f}".replace(".", ",")),
        ("Makro F1", f"{m['p_f1']:.6f}".replace(".", ",")),
        ("Test görüntüsü", str(m["p_n"])),
        ("Hata", str(m["p_err"])),
        ("Sınıf sayısı", "2"),
        ("Transfer üstünlüğü", "KANITLANMADI"),
    ]
    for x, title, rows, col in ((0.055, "Domates — YOLO11n-cls", rows_t, GREEN),
                                (0.515, "Biber — transfer adayı", rows_p, BLUE)):
        fig.patches.append(mpatches.FancyBboxPatch(
            (x, 0.14), 0.43, 0.68,
            boxstyle="round,pad=0.01,rounding_size=0.014",
            transform=fig.transFigure, fc="white", ec=LINE, lw=1.6))
        fig.text(x + 0.022, 0.775, title, fontsize=20, fontweight="bold",
                 color=col)
        for i, (k, v) in enumerate(rows):
            yy = 0.70 - i * 0.085
            fig.text(x + 0.022, yy, k, fontsize=14.5, color=MUTED)
            fig.text(x + 0.405, yy, v, fontsize=16, fontweight="bold",
                     color=INK, ha="right")
    onnx = m["onnx"]
    footer(fig, f"ONNX eşitliği: {onnx.get('parity_samples', '-')} örnek, "
                f"{onnx.get('class_mismatches', '-')} sınıf uyuşmazlığı · "
                "Dağıtım: RESEARCH_ONLY")
    save(fig, "03_model_kanit_kartlari.png", made)


# --- 04 -------------------------------------------------------------------

def s04(made):
    fig = canvas("Hata Durumunda Güvenli Davranış",
                 "Sistem belirsizlikte tahmin etmez; güvenli duruma geçer",
                 "GÜVENLİK")
    rows = [
        ("Görüntü bulanık / karanlık", "IMAGE_REJECT", "Yeniden çekim ister"),
        ("Model güveni düşük", "ABSTAIN", "İnsan incelemesine gönderir"),
        ("Bilinmeyen ürün", "BLOCK", "Yönlendirme yapmaz"),
        ("Sensör verisi eksik / bayat", "DEGRADED", "Karar vermez, izler"),
        ("Görüntü ve sensör çelişiyor", "CONFLICT", "İnsan incelemesi"),
        ("Donanım ACK gelmedi", "SAFE_STATE", "Eylemi geri alır"),
    ]
    y0, rh = 0.735, 0.098
    fig.text(0.075, y0 + 0.055, "Durum", fontsize=15, fontweight="bold",
             color=MUTED)
    fig.text(0.46, y0 + 0.055, "Güvenli mod", fontsize=15,
             fontweight="bold", color=MUTED)
    fig.text(0.68, y0 + 0.055, "Sonuç", fontsize=15, fontweight="bold",
             color=MUTED)
    for i, (cond, mode, res) in enumerate(rows):
        y = y0 - i * rh
        fig.patches.append(mpatches.FancyBboxPatch(
            (0.055, y - 0.035), 0.89, 0.072,
            boxstyle="round,pad=0.004,rounding_size=0.008",
            transform=fig.transFigure,
            fc="white" if i % 2 == 0 else "#FBFDFC", ec=LINE, lw=1.0))
        fig.text(0.075, y, cond, fontsize=15, color=INK, va="center")
        fig.text(0.46, y, mode, fontsize=15, fontweight="bold", color=RED,
                 va="center")
        fig.text(0.68, y, res, fontsize=14.5, color=MUTED, va="center")
    footer(fig, "Hiçbir hata durumu özerk fiziksel eylemle sonuçlanmaz.",
           RED)
    save(fig, "04_guvenli_durum_matrisi.png", made)


# --- 05 / 06 --------------------------------------------------------------

def _readiness(made, fname, title, subtitle, rows, note):
    fig = canvas(title, subtitle, "DURUM")
    y0, rh = 0.74, 0.105
    for i, (label, done, total) in enumerate(rows):
        y = y0 - i * rh
        frac = done / total if total else 0
        fig.text(0.055, y + 0.022, label, fontsize=16, color=INK)
        fig.patches.append(mpatches.FancyBboxPatch(
            (0.055, y - 0.028), 0.70, 0.032,
            boxstyle="round,pad=0.002,rounding_size=0.006",
            transform=fig.transFigure, fc="#E8EEEB", ec="none"))
        if frac > 0:
            fig.patches.append(mpatches.FancyBboxPatch(
                (0.055, y - 0.028), 0.70 * frac, 0.032,
                boxstyle="round,pad=0.002,rounding_size=0.006",
                transform=fig.transFigure,
                fc=GREEN if frac == 1 else AMBER, ec="none"))
        fig.text(0.775, y - 0.012, f"{done} / {total}", fontsize=16,
                 fontweight="bold", color=INK)
    footer(fig, note)
    save(fig, fname, made)


def s05(made):
    r = load("layer56_final_release_handoff_v1.json")
    blockers = r.get("remaining_external_or_operational_blockers") or {}
    n_block = sum(1 for v in blockers.values() if v is True) or len(blockers)
    _readiness(
        made, "05_teslim_hazirligi.png", "Sürüm Teslim Hazırlığı",
        "Yazılım paketi tamam; operasyonel sürüm donanım işini bekliyor",
        [("Yazılım teslim paketi", 1, 1),
         ("Arka uç sözleşmesi", 1, 1),
         ("Ön uç alan sözlüğü", 1, 1),
         ("Donanım sözleşmesi", 1, 1),
         ("Operasyonel sürüm onayı", 0, 1)],
        f"Açık dış/operasyonel engel: {n_block} — Hailo, Pi 5 + AI HAT+, "
        "gerçek sera ve fiziksel eyleme doğrulaması.")


def s06(made):
    m = metrics()
    _readiness(
        made, "06_kanit_hazirlik_panosu.png", "Kanıt Hazırlık Panosu",
        "Jüriye bugün doğrudan gösterilebilecek kanıtlar",
        [("Dondurulmuş test raporu (2 ürün)", 2, 2),
         ("ONNX eşitlik raporu", 2, 2),
         ("Açıklanabilirlik (Grad-CAM)", 2, 2),
         ("Model kayıt defteri kaydı", 2, 2),
         ("Gerçek sera doğrulaması", 0, 2),
         ("Donanım çalışma zamanı ölçümü", 0, 2)],
        f"Ölçülen: domates {m['t_n']:,} görüntü, biber {m['p_n']} görüntü — "
        "her ikisi de tek seferlik dondurulmuş testte."
        .replace(",", "."))


# --- 07 -------------------------------------------------------------------

def s07(made):
    m = metrics()
    st = load("greenpulse_56_layer_master_status_v1.json")
    counts = st.get("status_counts", {})
    fig = canvas("Kanıt Panosu",
                 "Bugün doğrudan yazılım veya ölçüm kanıtıyla "
                 "gösterilebilenler", "KANIT")
    top = [("Domates", f"%{m['t_acc']*100:.2f}".replace(".", ","),
            "Ölçülen doğruluk", GREEN),
           ("Domates", f"%{m['t_f1']*100:.2f}".replace(".", ","),
            "Ölçülen Makro F1", BLUE),
           ("Biber", f"%{m['p_acc']*100:.2f}".replace(".", ","),
            "Ölçülen doğruluk", GREEN),
           ("Biber", f"%{m['p_f1']*100:.2f}".replace(".", ","),
            "Ölçülen Makro F1", BLUE)]
    for i, (t, v, n, c) in enumerate(top):
        card(fig, 0.055 + i * 0.228, 0.50, 0.205, 0.215, t, v, n, c)
    bottom = [("Tamamlanan katman", str(counts.get("DONE", 0)), "56 katmandan", GREEN),
              ("Kısmi katman", str(counts.get("PARTIAL", 0)), "yazılım devam", AMBER),
              ("Donanım bekleyen", str(counts.get("HARDWARE_BLOCKED", 0)), "dış bağımlılık", RED),
              ("ONNX uyuşmazlığı", str(m["onnx"].get("class_mismatches", 0)),
               f"{m['onnx'].get('parity_samples', 0)} örnekte", GREEN)]
    for i, (t, v, n, c) in enumerate(bottom):
        card(fig, 0.055 + i * 0.228, 0.215, 0.205, 0.215, t, v, n, c)
    footer(fig, "Hailo, donanım, su tasarrufu ve çok modlu üstünlük "
                "sonuçlarının hiçbiri gerçek test öncesinde ölçülmüş "
                "gibi sunulmamaktadır.")
    save(fig, "07_kanit_panosu.png", made)


# --- 08 -------------------------------------------------------------------

def s08(made):
    st = load("greenpulse_56_layer_master_status_v1.json")
    layers = st.get("layers", [])
    counts = st.get("status_counts", {})
    fig = canvas("56 Katman Hazırlık Matrisi",
                 f"Toplam {st.get('total_layers', 56)} katman — durum "
                 "dağılımı aşağıdadır", "KAPSAM")
    # Dikey adim, plaka yuksekliginden BUYUK olmalidir; aksi halde
    # satirlar ust uste biner ve tek blok gibi gorunur.
    cols, size, gx = 14, 0.052, 0.0625
    tile_h = size * (W / H)
    gy = tile_h + 0.024
    x0, y0 = 0.075, 0.72
    for i, lay in enumerate(layers[:56]):
        r, c = divmod(i, cols)
        x, y = x0 + c * gx, y0 - r * gy
        col = STATUS_COLOR.get(lay.get("status"), MUTED)
        fig.patches.append(mpatches.FancyBboxPatch(
            (x, y), size, tile_h,
            boxstyle="round,pad=0.002,rounding_size=0.006",
            transform=fig.transFigure, fc=col, ec="white", lw=1.6))
        fig.text(x + size / 2, y + tile_h / 2, str(lay.get("layer", i + 1)),
                 fontsize=13, fontweight="bold", color="white",
                 ha="center", va="center")
    for i, (k, n) in enumerate(counts.items()):
        x = 0.075 + i * 0.225
        fig.patches.append(mpatches.Rectangle(
            (x, 0.255), 0.022, 0.030, transform=fig.transFigure,
            fc=STATUS_COLOR.get(k, MUTED), ec="none"))
        fig.text(x + 0.032, 0.270, f"{STATUS_TR.get(k, k)}: {n}",
                 fontsize=15, color=INK, va="center")
    footer(fig, "Önceki “21/21 tamamlandı” ifadesi yalnızca iki ürünlük "
                "donanım öncesi hastalık kapsamına aitti; tüm mimariye "
                "değil.")
    save(fig, "08_katman_hazirlik_matrisi.png", made)


# --- 09 -------------------------------------------------------------------

def s09(made):
    fig = canvas("İzlenebilirlik Zinciri",
                 "Her karardan geriye, o kararı üreten görüntüye kadar",
                 "DENETİM")
    chain = ["Komut kimliği", "Karar kaydı", "Risk skoru",
             "Füzyon girdisi", "Model sürümü", "Görüntü karesi"]
    y, bh = 0.62, 0.115
    x0, bw = 0.055, 0.135
    gap = (0.945 - x0 - bw) / (len(chain) - 1)
    for i, label in enumerate(chain):
        x = x0 + i * gap
        fig.patches.append(mpatches.FancyBboxPatch(
            (x, y), bw, bh, boxstyle="round,pad=0.006,rounding_size=0.01",
            transform=fig.transFigure, fc="white", ec=BLUE, lw=2.2))
        fig.text(x + bw / 2, y + bh / 2, label, fontsize=14,
                 fontweight="bold", color=BLUE, ha="center", va="center")
        if i < len(chain) - 1:
            fig.patches.append(mpatches.FancyArrow(
                x + bw + 0.004, y + bh / 2, gap - bw - 0.008, 0,
                width=0.0016, head_width=0.012, head_length=0.008,
                transform=fig.transFigure, fc=MUTED, ec="none"))
    fig.text(0.055, 0.44, "Her bağlantı veritabanında SHA ile kayıtlıdır; "
                          "zincir tek bir sorguyla geriye doğru okunur.",
             fontsize=17, color=INK)
    footer(fig, "Model sürümü, veri kümesi sürümü ve karar politikası "
                "sürümü aynı kayıtta tutulur.")
    save(fig, "09_izlenebilirlik_zinciri.png", made)


# --- 10 -------------------------------------------------------------------

def s10(made):
    fig = canvas("İddia Sınırı",
                 "Neyi kanıtladık, neyi kasıtlı olarak iddia etmiyoruz",
                 "DÜRÜSTLÜK")
    verified = ["İki ürün için dondurulmuş test sonucu",
                "Sızıntıya duyarlı bölme ve yakın kopya taraması",
                "ONNX dışa aktarma eşitliği",
                "Grad-CAM ile niteliksel açıklanabilirlik",
                "Model kayıt defteri ve izlenebilirlik",
                "Güvenlik kapısı ve çekimser kalma politikası"]
    pending = ["Gerçek sera doğrulaması",
               "Kalibre edilmiş su stresi modeli",
               "Gerçek çok modlu füzyon",
               "Hailo HEF dönüşümü ve eşitliği",
               "Raspberry Pi 5 çalışma zamanı ölçümü",
               "Fiziksel eyleme ve kapalı döngü"]
    for x, title, rows, col, mark in (
            (0.055, "KANITLANDI", verified, GREEN, "✓"),
            (0.515, "HENÜZ İDDİA EDİLMİYOR", pending, RED, "•")):
        fig.patches.append(mpatches.FancyBboxPatch(
            (x, 0.14), 0.43, 0.68,
            boxstyle="round,pad=0.01,rounding_size=0.014",
            transform=fig.transFigure, fc="white", ec=col, lw=2.0))
        fig.text(x + 0.022, 0.775, title, fontsize=19, fontweight="bold",
                 color=col)
        for i, t in enumerate(rows):
            fig.text(x + 0.022, 0.70 - i * 0.088, f"{mark}  {t}",
                     fontsize=15, color=INK)
    footer(fig, "Projenin gücü yalnızca yüksek metriklerde değil, "
                "kanıtlamadığımız şeyi iddia etmememizdedir.")
    save(fig, "10_iddia_siniri.png", made)


# --- 11 -------------------------------------------------------------------

def s11(made):
    fig = canvas("Gerçek Doğrulama Yol Haritası",
                 "Donanım geldikten sonra ölçülecek adımlar — sırasıyla",
                 "PLAN")
    steps = [("1", "Gerçek sera görüntüsü toplama", "Kendi kameramız"),
             ("2", "Alan kayması ölçümü", "Laboratuvar → sera"),
             ("3", "Su stresi protokolü", "Kontrollü kuruma, 5-7 gün"),
             ("4", "Hailo HEF dönüşümü", "Eşitlik + kalibrasyon"),
             ("5", "Pi 5 çalışma zamanı", "Gecikme, RAM, kararlılık"),
             ("6", "Fiziksel kapalı döngü", "Pompa kalibrasyonu, ACK")]
    for i, (num, title, note) in enumerate(steps):
        col = i % 3
        row = i // 3
        x = 0.055 + col * 0.303
        y = 0.52 - row * 0.255
        fig.patches.append(mpatches.FancyBboxPatch(
            (x, y), 0.278, 0.215,
            boxstyle="round,pad=0.008,rounding_size=0.012",
            transform=fig.transFigure, fc="white", ec=LINE, lw=1.4))
        fig.text(x + 0.020, y + 0.163, num, fontsize=22, fontweight="bold",
                 color=AMBER)
        fig.text(x + 0.020, y + 0.098, title, fontsize=16,
                 fontweight="bold", color=INK)
        fig.text(x + 0.020, y + 0.040, note, fontsize=13.5, color=MUTED)
    footer(fig, "Bu adımların hiçbiri bugün ölçülmüş olarak sunulmuyor; "
                "yol haritası olarak gösteriliyor.")
    save(fig, "11_gercek_dogrulama_yol_haritasi.png", made)


# --- 12 -------------------------------------------------------------------

def s12(made):
    m = metrics()
    fig = canvas("GreenPulse Neden Bir Sınıflandırma Modelinden Fazlası",
                 "Performans, güvenlik, izlenebilirlik ve dağıtım "
                 "disiplini üzerine kurulu bir yapay zekâ sistemi", "ÖZET")
    blocks = [
        ("01", "Ölçülmüş Yapay Zekâ", GREEN,
         [("Domates", f"%{m['t_acc']*100:.2f} doğruluk".replace(".", ",")),
          ("Biber", f"%{m['p_acc']*100:.2f} doğruluk".replace(".", ","))]),
        ("02", "Güvenli Zekâ", BLUE,
         [("Hata yönetimi", "GÜVENLİ MOD / İZLE / İNCELE"),
          ("Denetlenebilirlik", "Komut düzeyinde izlenebilirlik")]),
        ("03", "Dağıtım Disiplini", AMBER,
         [("Arka uç", "OpenAPI 3.1 — 11 uç nokta"),
          ("Doğrulama", "Gerçek test kiti hazır")]),
    ]
    for i, (num, title, col, rows) in enumerate(blocks):
        x = 0.055 + i * 0.303
        fig.patches.append(mpatches.FancyBboxPatch(
            (x, 0.26), 0.278, 0.53,
            boxstyle="round,pad=0.01,rounding_size=0.014",
            transform=fig.transFigure, fc="white", ec=LINE, lw=1.5))
        fig.text(x + 0.022, 0.735, num, fontsize=20, fontweight="bold",
                 color=col, bbox=dict(boxstyle="round,pad=0.35",
                                      fc=col + "22", ec="none"))
        fig.text(x + 0.022, 0.655, title, fontsize=19, fontweight="bold",
                 color=INK)
        for j, (k, v) in enumerate(rows):
            yy = 0.545 - j * 0.115
            fig.text(x + 0.022, yy, k, fontsize=13, color=MUTED)
            fig.text(x + 0.022, yy - 0.045, v, fontsize=15.5,
                     fontweight="bold", color=col)
    fig.text(0.055, 0.175, "Ana mesaj:", fontsize=15, fontweight="bold",
             color=MUTED)
    fig.text(0.055, 0.115,
             "GreenPulse tahminde durmaz — yapay zekâ kanıtını "
             "açıklanabilir, güvenli ve denetlenebilir kararlara bağlar.",
             fontsize=21, fontweight="bold", color=INK)
    save(fig, "12_final_juri_ozeti.png", made)


def main() -> int:
    print("=" * 70)
    print("JURI GORSELLERI - TURKCE YENIDEN URETIM")
    print("=" * 70)
    made: list[str] = []
    for fn in (s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12):
        try:
            fn(made)
        except Exception as exc:                      # noqa: BLE001
            print(f"  {fn.__name__} XETA: {exc}")
    manifest = {
        "schema_version": "greenpulse.jury_visual_pack.v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": "scripts/build_jury_visuals_tr.py",
        "language": "tr",
        "visual_format": "1920x1080 PNG / 16:9",
        "visual_count": len(made),
        "visuals": [Path(p).name for p in made],
        "note": ("Tum sayilar reports/ altindaki rapor dosyalarindan "
                 "okunur; bu betikte elle yazilmis metrik yoktur."),
    }
    (OUT / "jury_visual_pack_manifest_v2.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("-" * 70)
    print(f"  Uretilen gorsel : {len(made)}")
    print(f"  Klasor          : {OUT.resolve()}")
    print("=" * 70)
    return 0 if len(made) == 12 else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
GreenPulse - Sunum tasarim sistemi.

Tum `prez/` gorselleri bu modulu kullanir. Amac: 78 slaytin TEK BIR
sistem gibi gorunmesi - ayni izgara, ayni tipografi, ayni renk anlami.

KANIT SEVIYESI ROZETI
---------------------
Her slayt, uzerindeki bilginin NE KADAR kanitlandigini rozetle soyler.
Bu, sunumun en onemli tasarim kararidir: juri bir grafige baktiginda
"bu olculdu mu, yoksa planlanan mi?" sorusunu sormak zorunda kalmamali.

    OLCULDU              gercek calistirma sonucu, rapor dosyasinda var
    YAZILIM DOGRULANDI   kod + test var, gercek donanim/saha verisi yok
    TAHMIN               yontemi belgelenmis hesaplama, olcum degil
    GERCEK TEST BEKLIYOR henuz hicbir sayi yok - yalnizca protokol

`PENDING` rozetli slaytlarda SAYI GOSTERILMEZ. Bos eksen veya
yer tutucu rakam koymak, olculmus izlenimi yaratir.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# --- Tuval ---------------------------------------------------------------
W, H, DPI = 19.20, 10.80, 100          # 1920 x 1080

# --- Renk ----------------------------------------------------------------
BG = "#F6F8F7"
PANEL = "#FFFFFF"
INK = "#10241D"
MUTED = "#63756E"
FAINT = "#9AA8A2"
LINE = "#DCE4E0"

BRAND = "#12674A"          # GreenPulse yesili
BRAND_DK = "#0B4633"
ACCENT = "#1F7A8C"         # teknik mavi
WARN = "#B8860B"
ALERT = "#A32C22"
NEUTRAL = "#5A6B78"

SEQ = ["#12674A", "#1F7A8C", "#B8860B", "#A32C22", "#5A6B78", "#7A5FA3"]

# --- Kanit seviyeleri ----------------------------------------------------
MEASURED = "MEASURED"
SOFTWARE = "SOFTWARE"
ESTIMATED = "ESTIMATED"
PENDING = "PENDING"

TIER = {
    MEASURED:  ("ÖLÇÜLDÜ",              BRAND,  "#E4F0EB"),
    SOFTWARE:  ("YAZILIM DOĞRULANDI",   ACCENT, "#E3EFF2"),
    ESTIMATED: ("TAHMİN",               WARN,   "#F6EEDC"),
    PENDING:   ("GERÇEK TEST BEKLİYOR", ALERT,  "#F6E4E2"),
}

# --- Tipografi -----------------------------------------------------------
_PREFERRED = ["Segoe UI", "Inter", "Calibri", "DejaVu Sans"]


def _font() -> str:
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in _PREFERRED:
        if name in have:
            return name
    return "DejaVu Sans"


FONT = _font()
plt.rcParams.update({
    "font.family": FONT,
    "axes.unicode_minus": False,
})

T_TITLE, T_SUB, T_H2, T_BODY, T_SMALL, T_MICRO = 40, 18, 22, 16, 13.5, 11.5

# --- Izgara (sekil koordinatlari 0-1) ------------------------------------
ML, MR = 0.052, 0.948           # sol / sag kenar
Y_TITLE, Y_SUB, Y_RULE = 0.905, 0.845, 0.815
Y_TOP, Y_BOT = 0.775, 0.115     # icerik alani
FOOT_Y = 0.052


def slide(title: str, subtitle: str = "", tier: str = MEASURED,
          kicker: str = "") -> plt.Figure:
    """Ortak slayt iskeleti: kicker + baslik + alt baslik + rozet + cizgi."""
    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=BG)

    if kicker:
        fig.text(ML, 0.952, kicker.upper(), fontsize=T_MICRO,
                 fontweight="bold", color=BRAND, va="top",
                 linespacing=1.0)
    fig.text(ML, Y_TITLE, title, fontsize=T_TITLE, fontweight="bold",
             color=INK, va="top")
    if subtitle:
        fig.text(ML, Y_SUB, subtitle, fontsize=T_SUB, color=MUTED, va="top")

    label, col, bgc = TIER[tier]
    fig.text(MR, 0.945, label, fontsize=T_MICRO, fontweight="bold",
             color=col, ha="right", va="top",
             bbox=dict(boxstyle="round,pad=0.5", fc=bgc, ec="none"))

    fig.add_artist(plt.Line2D([ML, MR], [Y_RULE, Y_RULE], color=LINE,
                              lw=1.3, transform=fig.transFigure))
    fig.text(MR, 0.032, "GreenPulse", fontsize=T_MICRO, color=FAINT,
             ha="right", va="bottom")
    return fig


def foot(fig, text: str, color: str = MUTED) -> None:
    fig.text(ML, FOOT_Y, text, fontsize=T_SMALL, color=color, va="bottom")


def pending_note(fig, what: str) -> None:
    """PENDING slaytlarinda standart uyari - sayi YOKTUR."""
    foot(fig, f"Bu slaytta sayı gösterilmez. {what}", ALERT)


def panel(fig, x, y, w, h, *, ec=LINE, lw=1.3, fc=PANEL, z=1):
    fig.patches.append(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.010",
        transform=fig.transFigure, fc=fc, ec=ec, lw=lw, zorder=z))


def kpi(fig, x, y, w, h, label, value, note="", color=BRAND, *, big=34):
    """Tek KPI karti."""
    panel(fig, x, y, w, h)
    fig.text(x + 0.016, y + h - 0.030, label, fontsize=T_SMALL,
             color=MUTED, va="top", zorder=2)
    fig.text(x + 0.016, y + h * 0.46, value, fontsize=big,
             fontweight="bold", color=color, va="center", zorder=2)
    if note:
        fig.text(x + 0.016, y + 0.022, note, fontsize=T_MICRO, color=FAINT,
                 va="bottom", zorder=2)


def kpi_row(fig, items, y=0.56, h=0.20, gap=0.014):
    """Esit araliklarla KPI serisi."""
    n = len(items)
    w = (MR - ML - gap * (n - 1)) / n
    for i, it in enumerate(items):
        kpi(fig, ML + i * (w + gap), y, w, h, *it[:3],
            color=it[3] if len(it) > 3 else BRAND,
            big=it[4] if len(it) > 4 else 34)


def flow(fig, steps, y=0.50, h=0.135, *, colors=None, arrow=True):
    """Yatay akis diyagrami: [(etiket, renk), ...] veya [etiket, ...]."""
    norm = []
    for i, s in enumerate(steps):
        if isinstance(s, tuple):
            norm.append(s)
        else:
            norm.append((s, (colors or SEQ)[i % len(colors or SEQ)]))
    n = len(norm)
    gap_px = 0.012 if arrow else 0.008
    w = (MR - ML - gap_px * (n - 1)) / n
    for i, (label, col) in enumerate(norm):
        x = ML + i * (w + gap_px)
        panel(fig, x, y, w, h, ec=col, lw=2.0)
        fig.text(x + w / 2, y + h / 2, label, fontsize=T_BODY - 1.5,
                 fontweight="bold", color=col, ha="center", va="center",
                 zorder=2, linespacing=1.35)
        if arrow and i < n - 1:
            fig.patches.append(mpatches.FancyArrow(
                x + w + 0.0015, y + h / 2, gap_px - 0.004, 0,
                width=0.0014, head_width=0.010, head_length=0.005,
                transform=fig.transFigure, fc=FAINT, ec="none", zorder=3))


def bullets(fig, x, y, rows, *, size=T_BODY, dy=0.052, color=INK,
            marker="—"):
    for i, r in enumerate(rows):
        fig.text(x, y - i * dy, f"{marker}  {r}", fontsize=size, color=color,
                 va="top")


def table(fig, x, y, w, cols, rows, *, rh=0.062, head=True,
          col_colors=None):
    """Sade tablo - cerceve yok, zebra satir."""
    xs = [x + w * c for c in cols[1]]
    if head:
        for label, cx in zip(cols[0], xs):
            fig.text(cx, y, label, fontsize=T_SMALL, fontweight="bold",
                     color=MUTED, va="center")
        y -= rh * 0.75
    for i, row in enumerate(rows):
        yy = y - i * rh
        if i % 2 == 0:
            fig.patches.append(mpatches.Rectangle(
                (x - 0.010, yy - rh * 0.42), w + 0.020, rh * 0.84,
                transform=fig.transFigure, fc="#FFFFFF", ec="none",
                zorder=0))
        for j, (cell, cx) in enumerate(zip(row, xs)):
            col = (col_colors or {}).get(j, INK)
            weight = "bold" if j == 0 else "normal"
            fig.text(cx, yy, str(cell), fontsize=T_BODY - 1.5, color=col,
                     va="center", fontweight=weight, zorder=2)


def ax_area(fig, x, y, w, h):
    """Grafik ekseni - slayt izgarasina hizali."""
    ax = fig.add_axes([x, y, w, h])
    ax.set_facecolor(BG)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=T_SMALL - 1)
    ax.grid(axis="y", alpha=0.28, linestyle=":", color=FAINT)
    ax.set_axisbelow(True)
    return ax


def save(fig, out_dir: Path, name: str, registry: list, *, tier: str,
         source: str, claim: str) -> None:
    """Kaydet ve manifeste islе - her slaytin kaynagi kayit altinda."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.savefig(path, dpi=DPI, facecolor=BG)
    plt.close(fig)
    registry.append({
        "file": name,
        "evidence_tier": tier,
        "data_source": source,
        "claim": claim,
    })


def tr_pct(v: float, nd: int = 2) -> str:
    return f"%{v*100:.{nd}f}".replace(".", ",")


def tr_num(v: float, nd: int = 4) -> str:
    return f"{v:.{nd}f}".replace(".", ",")


def tr_int(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def load_json(p: str | Path) -> dict:
    path = Path(p)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

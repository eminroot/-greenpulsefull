"""
GreenPulse - Yarisma duzeyinde sunum paketi uretir  ->  `prez/`

    python -m scripts.build_prez

TASARIM SOZU
------------
Her slayt bir KANIT SEVIYESI rozeti tasir:

    OLCULDU              gercek calistirma sonucu (rapor dosyasindan)
    YAZILIM DOGRULANDI   kod + test var, gercek donanim/saha verisi yok
    TAHMIN               yontemi belgelenmis hesaplama
    GERCEK TEST BEKLIYOR henuz sayi yok - yalnizca protokol

EN ONEMLI KURAL: metrik veya donanim sonucu UYDURULMAZ.

Projedeki katman raporlarinin cogu su durumdadir:

    SOFTWARE_..._FRAMEWORK_COMPLETE_REAL_..._PENDING

Yani yazilim hazir, gercek olcum yok. Hailo, Raspberry Pi gecikmesi,
RAM/CPU/sicaklik, uzun sure kararliligi, gercek sulama ve su tasarrufu
icin projede TEK BIR olculmus sayi bulunmuyor. Bu slaytlar bos eksen
veya ornek rakamla DOLDURULMAZ; protokolu gosterir ve "olculmedi" der.

Sayilarin tamami `reports/` altindan OKUNUR. Bu dosyada elle yazilmis
metrik yoktur.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import prez_design as D  # noqa: E402

REPORTS = Path("reports")
OUT = Path("prez/slides")
PREZ = Path("prez")


# ---------------------------------------------------------------------------
# Veri katmani - tek kaynak
# ---------------------------------------------------------------------------


class Data:
    """Rapor dosyalarindan okunan degerler. Eksik anahtar SESSIZ gecmez."""

    def __init__(self) -> None:
        self.tomato = D.load_json(REPORTS / "tomato_final_test_v1.json")
        self.tomato_card = D.load_json(REPORTS / "tomato_model_card_v1.json")
        self.pepper = D.load_json(
            REPORTS / "pepper_final_test_v1" / "final_test_report.json")
        self.pepper_cmp = D.load_json(REPORTS / "pepper_model_comparison_v1.json")
        self.layers = D.load_json(
            REPORTS / "greenpulse_56_layer_master_status_v1.json")
        self.release = D.load_json(
            REPORTS / "layer56_final_release_handoff_v1.json")
        self.split = D.load_json(REPORTS / "tomato_split_v1" / "split_report.json")

    # -- metrikler ---------------------------------------------------------
    @property
    def t_metrics(self) -> dict:
        return self.tomato.get("metrics", {})

    @property
    def p_metrics(self) -> dict:
        return self.pepper.get("metrics", {})

    @property
    def t_per_class(self) -> dict:
        return self.tomato.get("per_class", {})

    @property
    def t_confusion(self) -> tuple[list[str], list[list[int]]]:
        cm = self.tomato.get("confusion_matrix", {})
        return cm.get("class_order", []), cm.get("matrix", [])

    @property
    def p_confusion(self) -> tuple[list[str], list[list[int]]]:
        cm = self.pepper.get("confusion_matrix", {})
        return cm.get("class_order", []), cm.get("values", [])

    @property
    def t_eval(self) -> dict:
        return self.tomato.get("evaluation", {})

    def n(self, block: dict, *keys: str) -> int:
        """
        Sayisal alan okuyucu - eksik anahtarda SESSIZCE 0 DONMEZ.

        Slayt 06'da `total_images` anahtari yoktu ve altyazi "0 görüntü"
        basildi. Sessiz sifir, olculmus veriyi yok gibi gosterir; bu
        yuzden artik istisna atiliyor.
        """
        for k in keys:
            v = block.get(k)
            if isinstance(v, (int, float)):
                return int(v)
        raise KeyError(f"sayisal alan bulunamadi: {keys}")

    @property
    def onnx(self) -> dict:
        return self.tomato_card.get("onnx", {})

    @property
    def status_counts(self) -> dict:
        return self.layers.get("status_counts", {})

    # -- tahminler ---------------------------------------------------------
    def predictions(self) -> list[dict]:
        p = REPORTS / "tomato_final_test_predictions_v1.csv"
        if not p.exists():
            return []
        with p.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def curve(self, rel: str) -> list[dict]:
        p = Path(rel)
        if not p.exists():
            return []
        with p.open(encoding="utf-8") as fh:
            return [{k.strip(): v.strip() for k, v in row.items() if k}
                    for row in csv.DictReader(fh)]


def short(name: str) -> str:
    """`Tomato___Spider_mites Two-spotted_spider_mite` -> `Spider mites`."""
    n = name.split("___")[-1].replace("_", " ")
    n = n.replace("Two-spotted spider mite", "").strip()
    return n[:22]


# ---------------------------------------------------------------------------


def main() -> int:
    from scripts import prez_parts_a as A
    from scripts import prez_parts_b as B

    print("=" * 74)
    print("GreenPulse - SUNUM PAKETI")
    print("=" * 74)

    if OUT.exists():
        for f in OUT.glob("*.png"):
            f.unlink()

    data = Data()
    reg: list[dict] = []

    for section in (A.build, B.build):
        section(data, OUT, reg)

    tiers: dict[str, int] = {}
    for item in reg:
        tiers[item["evidence_tier"]] = tiers.get(item["evidence_tier"], 0) + 1

    PREZ.mkdir(parents=True, exist_ok=True)
    (PREZ / "prez_manifest.json").write_text(json.dumps({
        "schema_version": "greenpulse.prez.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": "scripts/build_prez.py",
        "language": "tr",
        "format": "1920x1080 PNG / 16:9",
        "slide_count": len(reg),
        "evidence_tier_counts": tiers,
        "rule": ("Metrik ve donanim sonucu UYDURULMAZ. GERCEK TEST BEKLIYOR "
                 "rozetli slaytlarda sayi gosterilmez."),
        "slides": reg,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 74)
    for tier, n in sorted(tiers.items()):
        print(f"  {D.TIER[tier][0]:<24} {n:>3} slayt")
    print("-" * 74)
    print(f"  Toplam slayt : {len(reg)}")
    print(f"  Klasor       : {PREZ.resolve()}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
GreenPulse - Muhendislik teslim paketini ana projeyle esitler.

NEDEN BU BETIK VAR
------------------
`handoff/GreenPulse_Engineering_Handoff_PREOP` elle olusturulmus bir
anlik goruntuydu ve ESKIMISTI:

    handoff anlik goruntusu : 00:45
    juri materyali bitti    : 01:03   (18 dakika sonra)

Sonuc: teslim paketinde 5 dakikalik SUNUM SECKISININ TAMAMI, storyboard
ve 12 gorselden 6'si YOKTU. Paketi alan kisi jurinin gordugu materyali
goremezdi.

Elle kopyalamak ayni hatayi tekrar uretir. Bu betik esitlemeyi TEK
KOMUTA indirir ve `HANDOFF_FILE_MANIFEST_SHA256.json` dosyasini yeniden
uretir - aksi halde manifest bozulur ve butunluk kontrolu anlamsiz hale
gelir.

MODEL POLITIKASI
----------------
Teslim paketine yalnizca `.onnx` dosyalari girer. `.pt` agirliklari
kasten disarida birakilir: bu paket UC BIRIM dagitimi icindir, yeniden
egitim icin degil. Politika tek yerde tanimlidir (`MODEL_SUFFIXES`).

Calistirma:
    python -m scripts.sync_engineering_handoff
    python -m scripts.sync_engineering_handoff --check   (yalnizca rapor)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(".")
HANDOFF = Path("handoff/GreenPulse_Engineering_Handoff_PREOP")
MANIFEST = HANDOFF / "HANDOFF_FILE_MANIFEST_SHA256.json"

#: Paketin icerdigi ust duzey yollar.
MIRRORED = ("configs", "jury_evidence", "models", "prez", "release",
            "reports", "src", "tests")

#: Kok dizinden kopyalanan tekil dosyalar.
ROOT_FILES = ("requirements.txt", ".gitignore")

#: Teslim paketine giren model uzantilari - `.pt` KASTEN yok.
MODEL_SUFFIXES = {".onnx", ".json", ".names.json"}

#: Hicbir zaman kopyalanmayanlar.
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".venv"}


def wanted(rel: Path) -> bool:
    if any(part in SKIP_PARTS for part in rel.parts):
        return False
    # `.bak` yedekleri teslim paketine GIRMEZ: paketi acan gelistirici
    # `api.before_latest.bak` gorunce hangi dosyanin gercek oldugunu
    # sormak zorunda kalir. Yedekler ana projede kalir, pakete gitmez.
    if rel.suffix in {".pyc", ".pyo", ".bak"}:
        return False
    if rel.parts and rel.parts[0] == "models":
        return rel.suffix in MODEL_SUFFIXES
    return True


def collect() -> list[Path]:
    out: list[Path] = []
    for top in MIRRORED:
        base = ROOT / top
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.is_file():
                rel = f.relative_to(ROOT)
                if wanted(rel):
                    out.append(rel)
    for name in ROOT_FILES:
        if (ROOT / name).exists():
            out.append(Path(name))
    return sorted(out)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Teslim paketini esitler")
    ap.add_argument("--check", action="store_true",
                    help="Dosyalara DOKUNMADAN farki raporlar")
    args = ap.parse_args()

    if not HANDOFF.exists():
        print(f"  {HANDOFF} bulunamadi")
        return 1

    files = collect()
    added, updated, unchanged = [], [], 0

    for rel in files:
        src, dst = ROOT / rel, HANDOFF / rel
        if not dst.exists():
            added.append(rel)
        elif sha256(src) != sha256(dst):
            updated.append(rel)
        else:
            unchanged += 1

    # Pakette olup ana projede olmayanlar (artik gecersiz)
    stale = []
    for f in HANDOFF.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(HANDOFF)
        if rel.name in {"HANDOFF_FILE_MANIFEST_SHA256.json",
                        "HANDOFF_STATUS.json",
                        "START_HERE_ENGINEERING_HANDOFF.txt"}:
            continue
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if rel not in files:
            stale.append(rel)

    print("=" * 70)
    print("MUHENDISLIK TESLIM PAKETI - ESITLEME")
    print("=" * 70)
    print(f"  Ana projede izlenen dosya : {len(files)}")
    print(f"  Zaten ayni                : {unchanged}")
    print(f"  Pakette YOK (eklenecek)   : {len(added)}")
    print(f"  Degismis (guncellenecek)  : {len(updated)}")
    print(f"  Pakette fazla (silinecek) : {len(stale)}")

    for label, rows in (("EKLENECEK", added), ("GUNCELLENECEK", updated),
                        ("SILINECEK", stale)):
        if rows:
            print(f"\n  {label}:")
            for r in rows[:12]:
                print(f"    {r.as_posix()}")
            if len(rows) > 12:
                print(f"    ... +{len(rows) - 12}")

    if args.check:
        print("\n  --check modu: hicbir dosya degistirilmedi.")
        print("=" * 70)
        return 0 if not (added or updated or stale) else 1

    for rel in added + updated:
        dst = HANDOFF / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    for rel in stale:
        (HANDOFF / rel).unlink()

    # --- SHA manifesti YENIDEN URETILIR ---
    # Dosyalar degisip manifest eski kalirsa butunluk kontrolu
    # yaniltici olur: "dogrulama var" gorunur ama hicbir seyi dogrulamaz.
    entries = {}
    for f in sorted(HANDOFF.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(HANDOFF)
        if rel.name == MANIFEST.name or any(p in SKIP_PARTS for p in rel.parts):
            continue
        entries[rel.as_posix()] = {
            "sha256": sha256(f),
            "bytes": f.stat().st_size,
        }
    MANIFEST.write_text(json.dumps({
        "schema_version": "greenpulse.handoff_manifest.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "file_count": len(entries),
        "generated_by": "scripts/sync_engineering_handoff.py",
        "model_policy": "Yalnizca .onnx - .pt agirliklari kasten haric",
        "files": entries,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  Esitlendi. Manifest yeniden uretildi: {len(entries)} dosya")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

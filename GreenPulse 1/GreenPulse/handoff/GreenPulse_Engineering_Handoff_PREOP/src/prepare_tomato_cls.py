import csv
import os
import shutil
import json
from pathlib import Path
from collections import Counter

SOURCE = Path("reports/tomato_split_v1")
OUTPUT = Path("datasets/processed/tomato_cls")

summary = {}

for split, folder_name in [
    ("train", "train"),
    ("validation", "val"),
    ("test", "test")
]:
    manifest = SOURCE / f"{split}.csv"

    with open(manifest, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    counts = Counter()

    for row in rows:
        source = Path(row["image_path"])
        label = row["class_name"]

        if not source.is_file():
            raise FileNotFoundError(source)

        destination = OUTPUT / folder_name / label
        destination.mkdir(parents=True, exist_ok=True)

        target = destination / source.name

        if not target.exists():
            try:
                os.link(source, target)
            except OSError:
                shutil.copy2(source, target)

        if target.stat().st_size != source.stat().st_size:
            raise RuntimeError(f"File size mismatch: {target}")

        counts[label] += 1

    actual = sum(
        1 for p in (OUTPUT / folder_name).rglob("*")
        if p.suffix.lower() in (".jpg", ".jpeg", ".png")
    )

    if actual != len(rows):
        raise RuntimeError(
            f"{folder_name}: expected {len(rows)}, found {actual}"
        )

    summary[folder_name] = {
        "total": len(rows),
        "classes": dict(counts)
    }

    print(f"{folder_name.upper()}: {len(rows)} images")

report = Path("reports/tomato_classification_preparation.json")

report.write_text(
    json.dumps(summary, indent=4),
    encoding="utf-8"
)

print("\nGREENPULSE CLASSIFICATION DATASET READY")
print("Report:", report)

from pathlib import Path
from collections import defaultdict
import json
import csv

BASE = Path("datasets/raw/tomato/plantvillage_source")

with open(BASE / "leaf_grouping/leaf-map.json", encoding="utf-8") as f:
    leaf_map = json.load(f)

results = defaultdict(lambda: {
    "train_mapped": 0,
    "train_unmapped": 0,
    "test_mapped": 0,
    "test_unmapped": 0
})

for split in ["train", "test"]:

    split_file = BASE / f"splits/color_{split}.txt"

    paths = [
        x.strip().replace("\\", "/")
        for x in split_file.read_text(encoding="utf-8").splitlines()
        if "/Tomato___" in x
    ]

    for path in paths:
        parts = path.split("/")
        category = parts[-2]
        filename = parts[-1]

        original_name = filename.split("___", 1)[-1]
        key = Path(original_name).stem.strip().lower()

        values = leaf_map.get(key, [])

        matches = [
            value for value in values
            if value.startswith(category + ":::")
        ]

        status = "mapped" if len(matches) == 1 else "unmapped"

        results[category][f"{split}_{status}"] += 1

print("\nGREENPULSE CLASS COVERAGE AUDIT")
print("-" * 95)

print(
    f"{'CLASS':38}"
    f"{'TRAIN OK':>12}"
    f"{'TRAIN ?':>12}"
    f"{'TEST OK':>12}"
    f"{'TEST ?':>12}"
)

rows = []

for category, data in sorted(results.items()):
    row = {"class": category, **data}
    rows.append(row)

    print(
        f"{category:38}"
        f"{data['train_mapped']:>12}"
        f"{data['train_unmapped']:>12}"
        f"{data['test_mapped']:>12}"
        f"{data['test_unmapped']:>12}"
    )

output = Path("reports/tomato_mapping_coverage.csv")

with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "class",
            "train_mapped",
            "train_unmapped",
            "test_mapped",
            "test_unmapped"
        ]
    )

    writer.writeheader()
    writer.writerows(rows)

print("\nREPORT SAVED:", output)

from pathlib import Path
from collections import defaultdict
import hashlib
import json
import re

BASE = Path("datasets/raw/tomato")
SOURCE = BASE / "plantvillage_source"
IMAGES = BASE / "plantvillage_color"

with open(SOURCE / "leaf_grouping/leaf-map.json", encoding="utf-8") as f:
    leaf_map = json.load(f)

splits = {}
hash_groups = defaultdict(set)
leaf_groups = defaultdict(set)
missing = []
unmapped = defaultdict(int)

for split in ["train", "test"]:

    split_file = SOURCE / f"splits/color_{split}.txt"

    paths = [
        line.strip().replace("\\", "/")
        for line in split_file.read_text(encoding="utf-8").splitlines()
        if "/Tomato___" in line
    ]

    splits[split] = set(paths)

    for rel_path in paths:

        parts = rel_path.split("/")
        class_name = parts[2]
        filename = parts[3]

        local = IMAGES / class_name / filename

        if not local.is_file():
            missing.append(rel_path)
            continue

        file_hash = hashlib.sha256(local.read_bytes()).hexdigest()
        hash_groups[file_hash].add(split)

        identifier = filename.split("___")[-1]
        identifier = identifier.split("copy")[0]
        identifier = re.sub(
            r"\.(jpg|jpeg|png)$", "", identifier,
            flags=re.IGNORECASE
        ).strip().lower()

        suggestions = leaf_map.get(identifier, [])

        matches = [
            x for x in suggestions
            if x.startswith(class_name + ":::")
        ]

        if len(matches) == 1:
            leaf_groups[matches[0]].add(split)
        else:
            unmapped[split] += 1

cross_hash = sum(
    len(sides) > 1 for sides in hash_groups.values()
)

cross_leaf = sum(
    len(sides) > 1 for sides in leaf_groups.values()
)

report = {
    "train": len(splits["train"]),
    "test": len(splits["test"]),
    "overlapping_paths": len(splits["train"] & splits["test"]),
    "cross_split_exact_duplicates": cross_hash,
    "cross_split_known_leaf_groups": cross_leaf,
    "unmapped_train": unmapped["train"],
    "unmapped_test": unmapped["test"],
    "missing_files": len(missing)
}

Path("reports").mkdir(exist_ok=True)

with open(
    "reports/tomato_leakage_audit.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(report, f, indent=4)

print("\nGREENPULSE DATA LEAKAGE AUDIT")
print("--------------------------------")

for key, value in report.items():
    print(f"{key}: {value}")

print("--------------------------------")
print("Report saved successfully!")

import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

BASE = Path("reports/tomato_split_v1")
SOURCE = Path("datasets/raw/tomato/plantvillage_source")

splits = {}
hashes = defaultdict(set)
names = defaultdict(set)
leaves = defaultdict(set)
unknown = Counter()

leaf_map = json.loads(
    (SOURCE / "leaf_grouping/leaf-map.json").read_text(encoding="utf-8")
)

for split in ["train", "validation", "test"]:
    with open(BASE / f"{split}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    splits[split] = rows

    for row in rows:
        path = Path(row["image_path"])
        category = row["class_name"]

        assert path.is_file(), f"Missing image: {path}"

        hashes[row["sha256"]].add(split)

        original = path.name.split("___", 1)[-1]
        key = Path(original).stem.strip().lower()

        names[(category, key)].add(split)

        matches = [
            value for value in leaf_map.get(key, [])
            if value.startswith(category + ":::")
        ]

        if len(matches) == 1:
            leaves[matches[0]].add(split)
        else:
            unknown[split] += 1

print("\nGREENPULSE FINAL DATASET VERIFICATION")
print("-" * 75)

classes = sorted({
    row["class_name"]
    for rows in splits.values()
    for row in rows
})

print(f"{'CLASS':43} {'TRAIN':>7} {'VAL':>7} {'TEST':>7}")

for category in classes:
    counts = [
        sum(row["class_name"] == category for row in splits[s])
        for s in ["train", "validation", "test"]
    ]

    print(
        f"{category[:43]:43} "
        f"{counts[0]:7} {counts[1]:7} {counts[2]:7}"
    )

def overlaps(groups):
    return sum(len(sides) > 1 for sides in groups.values())

issues = {
    "cross_split_exact_duplicates": overlaps(hashes),
    "cross_split_original_names": overlaps(names),
    "cross_split_known_leaf_groups": overlaps(leaves),
    "classes_missing_from_a_split": sum(
        not any(row["class_name"] == category for row in splits[s])
        for category in classes
        for s in splits
    )
}

print("\nVERIFICATION RESULTS")
print("-" * 75)

for name, value in issues.items():
    print(f"{name}: {value}")

print("\nUNKNOWN LEAF GROUPS")
for split, count in unknown.items():
    print(f"{split}: {count}")

status = "PASS" if all(v == 0 for v in issues.values()) else "REVIEW_REQUIRED"

print("\nDATASET STRUCTURAL STATUS:", status)

report = {
    "status": status,
    "split_sizes": {s: len(rows) for s, rows in splits.items()},
    "issues": issues,
    "unknown_leaf_groups": dict(unknown)
}

(BASE / "verification_report.json").write_text(
    json.dumps(report, indent=4),
    encoding="utf-8"
)

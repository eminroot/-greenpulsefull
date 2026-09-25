from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import random
import json
import csv

BASE = Path("datasets/raw/tomato")
SOURCE = BASE / "plantvillage_source"
IMAGES = BASE / "plantvillage_color"
OUT = Path("reports/tomato_split_v1")

OUT.mkdir(parents=True, exist_ok=True)

leaf_map = json.loads(
    (SOURCE / "leaf_grouping/leaf-map.json").read_text(
        encoding="utf-8"
    )
)

records = []
parent = []
token_owner = {}

def find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]

def union(a, b):
    a, b = find(a), find(b)
    if a != b:
        parent[b] = a

for split in ["train", "test"]:
    file = SOURCE / f"splits/color_{split}.txt"

    paths = [
        x.strip().replace("\\", "/")
        for x in file.read_text(encoding="utf-8").splitlines()
        if "/Tomato___" in x
    ]

    for relative in paths:
        parts = relative.split("/")
        category = parts[-2]
        filename = parts[-1]

        image = IMAGES / category / filename
        digest = hashlib.sha256(image.read_bytes()).hexdigest()

        original = filename.split("___", 1)[-1]
        key = Path(original).stem.strip().lower()

        matches = [
            x for x in leaf_map.get(key, [])
            if x.startswith(category + ":::")
        ]

        tokens = [
            ("sha256", digest),
            ("original_name", category, key)
        ]

        if len(matches) == 1:
            tokens.append(("known_leaf", matches[0]))

        index = len(records)
        parent.append(index)

        records.append({
            "image_path": image.as_posix(),
            "class_name": category,
            "sha256": digest,
            "original_split": split,
            "leaf_mapping": (
                "KNOWN" if len(matches) == 1 else "UNKNOWN"
            )
        })

        for token in tokens:
            if token in token_owner:
                union(index, token_owner[token])
            else:
                token_owner[token] = index

groups = defaultdict(list)

for i in range(len(records)):
    groups[find(i)].append(i)

test_groups = {
    root for root, members in groups.items()
    if any(
        records[i]["original_split"] == "test"
        for i in members
    )
}

train_groups = defaultdict(list)
test_indices = []
excluded = 0

for root, members in groups.items():
    classes = {
        records[i]["class_name"] for i in members
    }

    if len(classes) != 1:
        raise RuntimeError(
            "Conflicting classes detected in a linked group"
        )

    if root in test_groups:
        for i in members:
            if records[i]["original_split"] == "test":
                test_indices.append(i)
            else:
                excluded += 1
    else:
        category = records[members[0]]["class_name"]
        train_groups[category].append(members)

rng = random.Random(42)

train_indices = []
val_indices = []

for category, category_groups in sorted(train_groups.items()):
    rng.shuffle(category_groups)

    total = sum(len(g) for g in category_groups)
    target = round(total * 0.15)
    selected = 0

    for position, group in enumerate(category_groups):
        remaining = len(category_groups) - position

        if selected < target and remaining > 1:
            val_indices.extend(group)
            selected += len(group)
        else:
            train_indices.extend(group)

def save_manifest(filename, indices):
    seen = set()
    rows = []

    for i in sorted(indices):
        row = records[i]

        if row["sha256"] in seen:
            continue

        seen.add(row["sha256"])
        rows.append(row)

    with open(
        OUT / filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(records[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)

    return rows

train = save_manifest("train.csv", train_indices)
val = save_manifest("validation.csv", val_indices)
test = save_manifest("test.csv", test_indices)

for a, b in [
    (train, val),
    (train, test),
    (val, test)
]:
    assert not (
        {x["sha256"] for x in a}
        &
        {x["sha256"] for x in b}
    )

report = {
    "train": len(train),
    "validation": len(val),
    "test": len(test),
    "excluded_train_due_to_test_group": excluded,
    "train_classes": dict(Counter(
        x["class_name"] for x in train
    )),
    "validation_classes": dict(Counter(
        x["class_name"] for x in val
    )),
    "test_classes": dict(Counter(
        x["class_name"] for x in test
    ))
}

(OUT / "split_report.json").write_text(
    json.dumps(report, indent=4),
    encoding="utf-8"
)

print("\nGREENPULSE SPLIT RESULTS")
print("--------------------------------")

for key in [
    "train",
    "validation",
    "test",
    "excluded_train_due_to_test_group"
]:
    print(f"{key}: {report[key]}")

print("--------------------------------")
print("Exact duplicate overlap: 0")
print("Known linked groups separated.")
print("Reports saved successfully.")

from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import json

BASE = Path("datasets/raw/tomato")
SOURCE = BASE / "plantvillage_source"
IMAGES = BASE / "plantvillage_color"

with open(SOURCE / "leaf_grouping/leaf-map.json", encoding="utf-8") as f:
    leaf_map = json.load(f)

hashes = defaultdict(lambda: defaultdict(list))
unmapped = Counter()
examples = []

for split in ["train", "test"]:
    file = SOURCE / f"splits/color_{split}.txt"

    paths = [
        x.strip().replace("\\", "/")
        for x in file.read_text(encoding="utf-8").splitlines()
        if "/Tomato___" in x
    ]

    for relative_path in paths:
        parts = relative_path.split("/")
        category = parts[-2]
        filename = parts[-1]

        image_path = IMAGES / category / filename

        digest = hashlib.sha256(
            image_path.read_bytes()
        ).hexdigest()

        hashes[digest][split].append(relative_path)

        key = filename.split("___")[-1]
        key = Path(key).stem.strip().lower()

        values = leaf_map.get(key)

        if values is None:
            reason = "KEY_NOT_FOUND"
        else:
            matches = [
                v for v in values
                if v.startswith(category + ":::")
            ]

            if len(matches) == 1:
                continue

            reason = (
                "CLASS_MISMATCH"
                if len(matches) == 0
                else "AMBIGUOUS"
            )

        unmapped[reason] += 1

        if len(examples) < 5:
            examples.append({
                "class": category,
                "filename": filename,
                "lookup_key": key,
                "reason": reason,
                "leaf_map_value": values
            })

conflicts = [
    record for record in hashes.values()
    if record["train"] and record["test"]
]

print("\nCROSS-SPLIT DUPLICATES")
print("----------------------------")

for i, group in enumerate(conflicts, 1):
    print(f"\nDUPLICATE GROUP {i}")
    print("TRAIN:", group["train"][:2])
    print("TEST:", group["test"][:2])

print("\nUNMAPPED REASONS")
print("----------------------------")

for reason, count in unmapped.items():
    print(reason, count)

print("\nUNMAPPED EXAMPLES")
print("----------------------------")

for example in examples:
    print(json.dumps(example, indent=2))

print("\nLEAF MAP SAMPLE")
print("----------------------------")

for key in list(leaf_map)[:2]:
    print(repr(key), repr(leaf_map[key]))

print("\nDIAGNOSTIC COMPLETED")

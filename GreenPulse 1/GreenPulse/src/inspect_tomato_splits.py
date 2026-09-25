from pathlib import Path
import json

source = Path("datasets/raw/tomato/plantvillage_source")

train_file = source / "splits/color_train.txt"
test_file = source / "splits/color_test.txt"
leaf_file = source / "leaf_grouping/leaf-map.json"

for file in [train_file, test_file, leaf_file]:
    if not file.exists():
        raise FileNotFoundError(f"Missing file: {file}")

train = {
    line.strip() for line in train_file.read_text().splitlines()
    if "/Tomato___" in line
}

test = {
    line.strip() for line in test_file.read_text().splitlines()
    if "/Tomato___" in line
}

with open(leaf_file, encoding="utf-8") as f:
    leaf_map = json.load(f)

print("\nGREENPULSE OFFICIAL SPLIT CHECK")
print("--------------------------------")
print("TRAIN:", len(train))
print("TEST:", len(test))
print("Overlapping filenames:", len(train & test))
print("Leaf map type:", type(leaf_map).__name__)

if isinstance(leaf_map, dict):
    print("Leaf map sample:")
    for key in list(leaf_map)[:2]:
        print(str(key)[:120], ":", str(leaf_map[key])[:150])

print("--------------------------------")
print("Metadata successfully loaded!")

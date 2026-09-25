from pathlib import Path
import hashlib
import csv

DATASET = Path("datasets/raw/tomato/plantvillage_color")
REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

seen = {}
unique = []
duplicates = []
conflicts = []

images = sorted(
    p for p in DATASET.rglob("*")
    if p.suffix.lower() in (".jpg", ".jpeg", ".png")
)

for path in images:
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    label = path.parent.name

    if file_hash in seen:
        original_path, original_label = seen[file_hash]

        if label != original_label:
            conflicts.append((str(path), str(original_path)))
        else:
            duplicates.append(
                (str(path), str(original_path), file_hash)
            )
    else:
        seen[file_hash] = (path, label)
        unique.append((str(path), label, file_hash))

if conflicts:
    raise RuntimeError(
        f"Cross-class conflicts found: {len(conflicts)}"
    )

with open(
    REPORTS / "tomato_clean_manifest.csv",
    "w",
    newline="",
    encoding="utf-8"
) as f:
    writer = csv.writer(f)
    writer.writerow(["image_path", "class_name", "sha256"])
    writer.writerows(unique)

with open(
    REPORTS / "tomato_excluded_duplicates.csv",
    "w",
    newline="",
    encoding="utf-8"
) as f:
    writer = csv.writer(f)
    writer.writerow(["excluded_image", "original_image", "sha256"])
    writer.writerows(duplicates)

print("\nGREENPULSE CLEAN DATASET")
print("---------------------------")
print("Original images:", len(images))
print("Unique images:", len(unique))
print("Excluded duplicates:", len(duplicates))
print("Cross-class conflicts:", len(conflicts))
print("---------------------------")
print("Clean manifest saved successfully.")

from pathlib import Path
from PIL import Image, ImageOps
from collections import defaultdict
import hashlib
import csv
import json

DATASET = Path("datasets/raw/tomato/plantvillage_color")
REPORTS = Path("reports")

exact = defaultdict(list)
visual = defaultdict(list)

def dhash(image):
    image = ImageOps.exif_transpose(image)
    image = image.convert("L").resize((9, 8))

    pixels = list(image.getdata())
    bits = 0

    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            bits = (bits << 1) | (left > right)

    return f"{bits:016x}"

images = sorted(
    p for p in DATASET.rglob("*")
    if p.suffix.lower() in (".jpg", ".jpeg", ".png")
)

print("Scanning images:", len(images))

for index, path in enumerate(images, 1):

    file_hash = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    with Image.open(path) as img:
        visual_hash = dhash(img)

    exact[file_hash].append(str(path))
    visual[visual_hash].append((str(path), file_hash))

    if index % 3000 == 0:
        print("Checked:", index)

exact_groups = [
    paths for paths in exact.values()
    if len(paths) > 1
]

visual_candidates = [
    items for items in visual.values()
    if len(items) > 1
    and len({item[1] for item in items}) > 1
]

conflicts = [
    group for group in exact_groups
    if len({Path(p).parent.name for p in group}) > 1
]

with open(
    REPORTS / "tomato_duplicate_candidates.csv",
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.writer(f)
    writer.writerow(["group", "type", "image_path"])

    for i, group in enumerate(exact_groups):
        for path in group:
            writer.writerow([i, "EXACT", path])

    for i, group in enumerate(visual_candidates):
        for path, _ in group:
            writer.writerow([i, "VISUAL_CANDIDATE", path])

summary = {
    "total_images": len(images),
    "exact_duplicate_groups": len(exact_groups),
    "visual_candidate_groups": len(visual_candidates),
    "exact_cross_class_conflicts": len(conflicts)
}

with open(
    REPORTS / "tomato_duplicate_report.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\nGREENPULSE DUPLICATE AUDIT")
print("---------------------------")

for key, value in summary.items():
    print(f"{key}: {value}")

print("---------------------------")
print("Reports saved successfully.")

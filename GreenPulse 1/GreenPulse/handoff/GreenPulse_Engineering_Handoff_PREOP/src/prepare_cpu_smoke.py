import csv
import os
import random
import shutil
from pathlib import Path
from collections import defaultdict

SOURCE = Path("reports/tomato_split_v1")
OUTPUT = Path("datasets/processed/tomato_smoke")

rng = random.Random(42)

for split, folder, limit in [
    ("train", "train", 30),
    ("validation", "val", 10)
]:
    groups = defaultdict(list)

    with open(
        SOURCE / f"{split}.csv",
        encoding="utf-8"
    ) as f:
        for row in csv.DictReader(f):
            groups[row["class_name"]].append(
                Path(row["image_path"])
            )

    total = 0

    for category, images in sorted(groups.items()):
        rng.shuffle(images)
        selected = images[:limit]

        if len(selected) < limit:
            raise RuntimeError(
                f"Insufficient images: {category}"
            )

        destination = OUTPUT / folder / category
        destination.mkdir(parents=True, exist_ok=True)

        for image in selected:
            target = destination / image.name

            if not target.exists():
                try:
                    os.link(image, target)
                except OSError:
                    shutil.copy2(image, target)

            total += 1

    print(f"{folder.upper()}: {total} images")

print("\nGREENPULSE CPU TRAINING DATA READY!")

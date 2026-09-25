
import hashlib
import json

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]

DATA = (
    ROOT /
    "datasets/external/plantvillage_pepper_source"
)

INPUT = (
    ROOT / "reports/pepper_dataset_audit_v1.json"
)

OUTPUT = (
    ROOT / "reports/pepper_near_duplicate_audit_v1.json"
)

# These are exploratory screening thresholds.
# They are NOT validated duplicate-classification limits.
DHASH_MAX_DISTANCE = 3
PHASH_MAX_DISTANCE = 5

MAX_EXAMPLES_PER_CATEGORY = 100


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b""
        ):
            digest.update(block)

    return digest.hexdigest()


def bits_to_integer(bits):
    packed = np.packbits(
        bits.reshape(-1).astype(np.uint8)
    )

    return int.from_bytes(
        packed.tobytes(),
        byteorder="big"
    )


def image_fingerprint(path):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("L")

        # Difference hash: image structure.
        small = np.asarray(
            image.resize(
                (9, 8),
                Image.Resampling.LANCZOS
            ),
            dtype=np.uint8
        )

        dhash = bits_to_integer(
            small[:, 1:] > small[:, :-1]
        )

        # Perceptual hash: low-frequency
        # image information using DCT.
        large = np.asarray(
            image.resize(
                (32, 32),
                Image.Resampling.LANCZOS
            ),
            dtype=np.float32
        )

        dct = cv2.dct(large)

        coefficients = (
            dct[:8, :8]
            .reshape(-1)[1:]
        )

        median = np.median(coefficients)

        phash = bits_to_integer(
            coefficients > median
        )

    return dhash, phash


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            "Near-duplicate report already exists."
        )

    audit = json.loads(
        INPUT.read_text(
            encoding="utf-8-sig"
        )
    )

    records = audit["samples"]

    assert len(records) == 2475, (
        "Dataset count changed. Review required."
    )

    fingerprints = []

    print("--------------------------------")
    print("GREENPULSE PEPPER NEAR-DUPLICATE")
    print("--------------------------------")
    print("Checking source integrity...")

    for index, record in enumerate(records, 1):
        relative = Path(record["path"])

        path = (DATA / relative).resolve()

        if not path.is_relative_to(DATA.resolve()):
            raise ValueError(
                "Image path escapes dataset directory."
            )

        if not path.is_file():
            raise FileNotFoundError(path)

        # Reject a modified dataset rather than
        # silently auditing different content.
        if file_hash(path) != record["sha256"]:
            raise ValueError(
                f"Source image changed: {relative}"
            )

        dhash, phash = image_fingerprint(path)

        fingerprints.append({
            "path": record["path"],
            "class_name": record["class_name"],
            "leaf_group_id": record["leaf_group_id"],
            "dhash": dhash,
            "phash": phash
        })

        if index % 500 == 0:
            print(
                f"Fingerprints: {index}/{len(records)}"
            )

    # Compare each unique pair once.
    counts = Counter()

    examples = {
        "same_leaf_group": [],
        "different_mapped_groups": [],
        "unknown_leaf_group": [],
        "cross_class": []
    }

    flagged_cross_group_images = set()

    total_comparisons = 0

    print("Screening visually similar images...")

    for i, first in enumerate(fingerprints):

        for second in fingerprints[i + 1:]:
            total_comparisons += 1

            d_distance = (
                first["dhash"] ^ second["dhash"]
            ).bit_count()

            if d_distance > DHASH_MAX_DISTANCE:
                continue

            p_distance = (
                first["phash"] ^ second["phash"]
            ).bit_count()

            if p_distance > PHASH_MAX_DISTANCE:
                continue

            group_a = first["leaf_group_id"]
            group_b = second["leaf_group_id"]

            if first["class_name"] != second["class_name"]:
                category = "cross_class"

            elif group_a is None or group_b is None:
                category = "unknown_leaf_group"

            elif group_a == group_b:
                category = "same_leaf_group"

            else:
                category = "different_mapped_groups"

            counts[category] += 1

            if category != "same_leaf_group":
                flagged_cross_group_images.add(
                    first["path"]
                )

                flagged_cross_group_images.add(
                    second["path"]
                )

            if (
                len(examples[category])
                < MAX_EXAMPLES_PER_CATEGORY
            ):
                examples[category].append({
                    "image_a": first["path"],
                    "image_b": second["path"],
                    "leaf_group_a": group_a,
                    "leaf_group_b": group_b,
                    "dhash_distance": d_distance,
                    "phash_distance": p_distance
                })

    report = {
        "audit_version": "0.1.0",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "project": "GreenPulse",
        "crop": "bell_pepper",
        "task": "DISEASE_CLASSIFICATION",
        "total_images": len(records),
        "total_pairs_compared": total_comparisons,
        "screening_method": {
            "algorithms": ["dHash", "pHash"],
            "maximum_dhash_distance":
                DHASH_MAX_DISTANCE,
            "maximum_phash_distance":
                PHASH_MAX_DISTANCE,
            "thresholds_validated": False
        },
        "candidate_pair_counts": dict(counts),
        "flagged_cross_group_image_count":
            len(flagged_cross_group_images),
        "flagged_cross_group_image_paths": sorted(
            flagged_cross_group_images
        ),
        "candidate_examples": examples,
        "human_review_completed": False,
        "physical_plant_identity_verified": False,
        "leakage_safe_split_verified": False,
        "images_automatically_removed": 0,
        "transfer_learning_started": False,
        "real_greenhouse_validation": False,
        "water_stress_validated": False
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )

    print()
    print("DATASET:", len(records), "images")

    print(
        "Pairs compared:",
        total_comparisons
    )

    for category in examples:
        print(
            category + ":",
            counts[category]
        )

    print(
        "Images flagged for cross-group review:",
        len(flagged_cross_group_images)
    )

    print()
    print("Human review: PENDING")
    print("Leakage-safe split: PENDING")
    print("Physical plant identity: UNVERIFIED")
    print("Images deleted: 0")
    print("Transfer learning: NOT STARTED")
    print()
    print("REPORT:", OUTPUT)
    print("--------------------------------")
    print("PEPPER NEAR-DUPLICATE AUDIT: PASS")


if __name__ == "__main__":
    main()

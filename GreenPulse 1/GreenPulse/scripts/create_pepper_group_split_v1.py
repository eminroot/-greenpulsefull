
import hashlib
import json
import os
import random
import tempfile

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / (
    "datasets/external/"
    "plantvillage_pepper_source"
)

AUDIT = ROOT / (
    "reports/pepper_dataset_audit_v1.json"
)

NEAR_AUDIT = ROOT / (
    "reports/pepper_near_duplicate_audit_v1.json"
)

OUTPUT = ROOT / (
    "reports/pepper_group_split_v1.json"
)

SEED = 2026

RATIOS = {
    "train": 0.70,
    "val": 0.15,
    "test": 0.15
}

SPLITS = tuple(RATIOS)


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def allocate_groups(groups, class_name):
    """
    Assign complete leaf groups to splits.

    Multiple deterministic candidates are tried.
    Selection uses only group sizes and labels,
    never model predictions or test performance.
    """

    if len(groups) < 3:
        raise ValueError(
            "Insufficient groups for three splits."
        )

    total = sum(
        len(items)
        for items in groups.values()
    )

    targets = {
        name: total * ratio
        for name, ratio in RATIOS.items()
    }

    best = None
    best_score = float("inf")

    for trial in range(128):
        rng = random.Random(
            f"{SEED}:{class_name}:{trial}"
        )

        items = list(groups.items())
        rng.shuffle(items)

        # Large groups are assigned first.
        # Randomized order resolves equal sizes.
        items.sort(
            key=lambda item: -len(item[1])
        )

        counts = {
            name: 0
            for name in SPLITS
        }

        assignments = {
            name: []
            for name in SPLITS
        }

        for index, (group_id, images) in enumerate(
            items
        ):
            size = len(images)

            empty = [
                name
                for name in SPLITS
                if not assignments[name]
            ]

            remaining = len(items) - index

            # Reserve enough groups to keep
            # every split represented.
            options = (
                empty
                if remaining == len(empty)
                else list(SPLITS)
            )

            rng.shuffle(options)

            def placement_score(name):
                proposed = dict(counts)
                proposed[name] += size

                return sum(
                    (
                        proposed[split]
                        - targets[split]
                    ) ** 2
                    / max(targets[split], 1)
                    for split in SPLITS
                )

            chosen = min(
                options,
                key=placement_score
            )

            assignments[chosen].append(
                group_id
            )

            counts[chosen] += size

        if any(
            not assignments[name]
            for name in SPLITS
        ):
            continue

        score = sum(
            abs(
                counts[name] - targets[name]
            ) / total
            for name in SPLITS
        )

        if score < best_score:
            best_score = score
            best = {
                group_id: name
                for name in SPLITS
                for group_id in assignments[name]
            }

    if best is None:
        raise ValueError(
            "Unable to construct grouped split."
        )

    return best


def verify_assignments(samples):
    """
    Validate disjoint image hashes,
    paths and claimed leaf groups.
    """

    paths = {
        name: set()
        for name in SPLITS
    }

    hashes = {
        name: set()
        for name in SPLITS
    }

    groups = {
        name: set()
        for name in SPLITS
    }

    classes = {
        name: set()
        for name in SPLITS
    }

    for sample in samples:
        split = sample["split"]

        paths[split].add(
            sample["path"]
        )

        hashes[split].add(
            sample["sha256"]
        )

        groups[split].add(
            sample["leaf_group_id"]
        )

        classes[split].add(
            sample["class_name"]
        )

    for index, first in enumerate(SPLITS):
        for second in SPLITS[index + 1:]:
            assert paths[first].isdisjoint(
                paths[second]
            )

            assert hashes[first].isdisjoint(
                hashes[second]
            )

            assert groups[first].isdisjoint(
                groups[second]
            )

    expected_classes = {
        "Pepper,_bell___Bacterial_spot",
        "Pepper,_bell___healthy"
    }

    for split in SPLITS:
        assert classes[split] == expected_classes

    return True


def main():
    print("--------------------------------")
    print("GREENPULSE GROUP-AWARE SPLITTING")
    print("--------------------------------")

    if OUTPUT.exists():
        raise FileExistsError(
            "Split manifest already exists."
        )

    audit = json.loads(
        AUDIT.read_text(
            encoding="utf-8-sig"
        )
    )

    near = json.loads(
        NEAR_AUDIT.read_text(
            encoding="utf-8-sig"
        )
    )

    records = audit["samples"]

    assert len(records) == 2475
    assert near["total_images"] == len(records)

    assert not audit["invalid_images"]
    assert not audit[
        "cross_class_duplicate_groups"
    ]

    assert (
        audit["exact_duplicate_groups"]
        == 0
    )

    assert not audit["leaf_metadata"][
        "group_class_conflicts"
    ]

    # Do not silently split data when the
    # previous screening flagged pairs
    # requiring cross-group review.
    pair_counts = near[
        "candidate_pair_counts"
    ]

    for category in (
        "different_mapped_groups",
        "unknown_leaf_group",
        "cross_class"
    ):
        if pair_counts.get(category, 0) != 0:
            raise ValueError(
                "Unresolved near-duplicate review: "
                + category
            )

    assert (
        near["flagged_cross_group_image_count"]
        == 0
    )

    assert not near[
        "human_review_completed"
    ]

    grouped = defaultdict(
        lambda: defaultdict(list)
    )

    excluded = []
    seen_hashes = set()
    seen_paths = set()
    group_classes = {}

    print("Verifying source images...")

    for record in records:
        relative = Path(
            record["path"]
        )

        path = (
            DATA / relative
        ).resolve()

        if not path.is_relative_to(
            DATA.resolve()
        ):
            raise ValueError(
                "Unsafe dataset path."
            )

        if not path.is_file():
            raise FileNotFoundError(path)

        if record["path"] in seen_paths:
            raise ValueError(
                "Duplicate dataset path."
            )

        seen_paths.add(
            record["path"]
        )

        digest = sha256_file(path)

        if digest != record["sha256"]:
            raise ValueError(
                "Source image integrity changed."
            )

        if digest in seen_hashes:
            raise ValueError(
                "Duplicate image content detected."
            )

        seen_hashes.add(digest)

        if not record["image_readable"]:
            raise ValueError(
                "Unreadable image in source audit."
            )

        group_id = record[
            "leaf_group_id"
        ]

        if group_id is None:
            excluded.append({
                "path": record["path"],
                "reason": "LEAF_GROUP_UNMAPPED"
            })

            continue

        class_name = record[
            "class_name"
        ]

        previous = group_classes.get(
            group_id
        )

        if (
            previous is not None
            and previous != class_name
        ):
            raise ValueError(
                "Leaf group crosses class labels."
            )

        group_classes[group_id] = (
            class_name
        )

        grouped[class_name][
            group_id
        ].append(record)

    expected_classes = {
        "Pepper,_bell___Bacterial_spot",
        "Pepper,_bell___healthy"
    }

    assert set(grouped) == expected_classes

    assert len(excluded) == 2, (
        "Unexpected unmapped sample count."
    )

    print(
        "Eligible images:",
        len(records) - len(excluded)
    )

    print(
        "Excluded images:",
        len(excluded)
    )

    print(
        "Mapped leaf groups:",
        len(group_classes)
    )

    assignments = {}

    for class_name in sorted(grouped):
        class_assignment = allocate_groups(
            grouped[class_name],
            class_name
        )

        assignments.update(
            class_assignment
        )

    samples = []

    for record in records:
        group_id = record[
            "leaf_group_id"
        ]

        if group_id is None:
            continue

        samples.append({
            "path": record["path"],
            "class_name": record["class_name"],
            "leaf_group_id": group_id,
            "sha256": record["sha256"],
            "split": assignments[group_id]
        })

    samples.sort(
        key=lambda item: item["path"]
    )

    verify_assignments(samples)

    summary = {}

    print()
    print("FINAL GROUPED DISTRIBUTION")

    for split in SPLITS:
        selected = [
            item
            for item in samples
            if item["split"] == split
        ]

        class_counts = {}

        for class_name in sorted(
            expected_classes
        ):
            class_counts[class_name] = sum(
                item["class_name"] == class_name
                for item in selected
            )

        summary[split] = {
            "images": len(selected),
            "percentage": round(
                len(selected)
                / len(samples)
                * 100,
                2
            ),
            "leaf_groups": len({
                item["leaf_group_id"]
                for item in selected
            }),
            "class_counts": class_counts
        }

        print(
            split.upper(),
            "|",
            len(selected),
            "images |",
            summary[split]["percentage"],
            "% |",
            summary[split]["leaf_groups"],
            "groups"
        )

        print(
            "  Bacterial spot:",
            class_counts[
                "Pepper,_bell___Bacterial_spot"
            ]
        )

        print(
            "  Healthy:",
            class_counts[
                "Pepper,_bell___healthy"
            ]
        )

    # Catch serious distribution errors.
    for split, details in summary.items():
        target = RATIOS[split] * 100

        if abs(
            details["percentage"] - target
        ) > 10:
            raise ValueError(
                "Split distribution requires review: "
                + split
            )

    manifest = {
        "manifest_version": "1.0",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "project": "GreenPulse",
        "crop": "bell_pepper",
        "task": "DISEASE_CLASSIFICATION",
        "source_audit_sha256": sha256_file(
            AUDIT
        ),
        "near_duplicate_audit_sha256":
            sha256_file(NEAR_AUDIT),
        "random_seed": SEED,
        "target_ratios": RATIOS,
        "summary": summary,
        "eligible_images": len(samples),
        "excluded_images": excluded,
        "claimed_leaf_group_count": len(
            group_classes
        ),
        "group_overlap_detected": False,
        "exact_hash_overlap_detected": False,
        "near_duplicate_screening_exhaustive": False,
        "physical_plant_identity_verified": False,
        "source_license_review_completed": False,
        "test_set_policy":
            "RESERVED_FOR_FINAL_EVALUATION_ONLY",
        "transfer_learning_started": False,
        "real_greenhouse_validation": False,
        "water_stress_validated": False,
        "samples": samples
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".pepper-split-",
            suffix=".tmp",
            dir=OUTPUT.parent,
            delete=False
        ) as stream:
            temporary = Path(
                stream.name
            )

            json.dump(
                manifest,
                stream,
                indent=2,
                ensure_ascii=False,
                allow_nan=False
            )

            stream.write("\n")

        os.replace(
            temporary,
            OUTPUT
        )

    finally:
        if (
            temporary is not None
            and temporary.exists()
        ):
            temporary.unlink()

    print()
    print("Group overlap: NONE DETECTED")
    print("Exact hash overlap: NONE DETECTED")
    print("Test set: RESERVED")
    print("Physical plant identity: UNVERIFIED")
    print("License review: PENDING")
    print("Transfer learning: NOT STARTED")
    print("Report:", OUTPUT)
    print("--------------------------------")
    print("PEPPER GROUP SPLIT: PASS")


if __name__ == "__main__":
    main()


import csv
import hashlib
import json
import math

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import torch
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]

REPORTS = ROOT / "reports"

SPLIT = REPORTS / "pepper_group_split_v1.json"

TRANSFER_TRAINING = (
    REPORTS / "pepper_transfer_training_v1.json"
)

BASELINE_TRAINING = (
    REPORTS / "pepper_generic_baseline_training_v1.json"
)

TRANSFER_VALIDATION = (
    REPORTS / "pepper_validation_evaluation_v1.json"
)

BASELINE_OUTPUT = (
    REPORTS / "pepper_generic_baseline_validation_v1.json"
)

COMPARISON_OUTPUT = (
    REPORTS / "pepper_model_comparison_v1.json"
)

PREDICTIONS_OUTPUT = (
    REPORTS / "pepper_paired_validation_predictions_v1.csv"
)

DATASET = ROOT / (
    "datasets/processed/pepper_cls_leafgroup_v1"
)

CLASSES = [
    "bacterial_spot",
    "healthy"
]

CLASS_MAPPING = {
    "Pepper,_bell___Bacterial_spot": 0,
    "Pepper,_bell___healthy": 1
}


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b""
        ):
            digest.update(block)

    return digest.hexdigest()


def load_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def calculate_metrics(confusion):
    per_class = {}

    for index, name in enumerate(CLASSES):
        tp = confusion[index][index]

        fn = sum(confusion[index]) - tp

        fp = sum(
            row[index] for row in confusion
        ) - tp

        support = tp + fn

        precision = (
            tp / (tp + fp)
            if tp + fp else 0.0
        )

        recall = (
            tp / support
            if support else 0.0
        )

        f1 = (
            2 * precision * recall
            / (precision + recall)
            if precision + recall else 0.0
        )

        per_class[name] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    total = sum(
        sum(row) for row in confusion
    )

    correct = sum(
        confusion[i][i]
        for i in range(2)
    )

    return {
        "accuracy": correct / total,
        "balanced_accuracy": sum(
            item["recall"]
            for item in per_class.values()
        ) / 2,
        "macro_precision": sum(
            item["precision"]
            for item in per_class.values()
        ) / 2,
        "macro_recall": sum(
            item["recall"]
            for item in per_class.values()
        ) / 2,
        "macro_f1": sum(
            item["f1"]
            for item in per_class.values()
        ) / 2,
        "per_class": per_class
    }


print("=" * 48)
print("GREENPULSE PEPPER MODEL COMPARISON")
print("=" * 48)


# 1. PREFLIGHT

for output in (
    BASELINE_OUTPUT,
    COMPARISON_OUTPUT,
    PREDICTIONS_OUTPUT
):
    if output.exists():
        raise FileExistsError(
            f"Output already exists: {output}"
        )

split = load_json(SPLIT)
transfer_training = load_json(TRANSFER_TRAINING)
baseline_training = load_json(BASELINE_TRAINING)
previous_validation = load_json(
    TRANSFER_VALIDATION
)

split_hash = sha256_file(SPLIT)

assert (
    previous_validation["split_manifest_sha256"]
    == split_hash
)

assert (
    baseline_training["split_manifest_sha256"]
    == split_hash
)

assert (
    previous_validation["test_images_evaluated"]
    == 0
)

assert not (DATASET / "test").exists()


# 2. VERIFY GROUP SEPARATION

groups = {
    name: {
        item["leaf_group_id"]
        for item in split["samples"]
        if item["split"] == name
    }
    for name in ("train", "val", "test")
}

assert groups["train"].isdisjoint(groups["val"])
assert groups["train"].isdisjoint(groups["test"])
assert groups["val"].isdisjoint(groups["test"])


# 3. VERIFY VALIDATION IMAGES

records = [
    item
    for item in split["samples"]
    if item["split"] == "val"
]

assert len(records) == 371
assert len(groups["val"]) == 51

verified = []
expected_paths = set()

print("\nVerifying validation images...")

for item in records:
    class_id = CLASS_MAPPING[
        item["class_name"]
    ]

    path = (
        DATASET
        / "val"
        / CLASSES[class_id]
        / Path(item["path"]).name
    ).resolve()

    if not path.is_relative_to(
        DATASET.resolve()
    ):
        raise ValueError(
            "Unsafe validation image path."
        )

    if not path.is_file():
        raise FileNotFoundError(path)

    if sha256_file(path) != item["sha256"]:
        raise ValueError(
            "Validation image integrity failure."
        )

    key = str(path).casefold()

    if key in expected_paths:
        raise ValueError(
            "Duplicate validation image path."
        )

    expected_paths.add(key)

    verified.append({
        "path": item["path"],
        "absolute_path": str(path),
        "true_id": class_id,
        "leaf_group_id": item["leaf_group_id"]
    })

actual_paths = {
    str(path.resolve()).casefold()
    for name in CLASSES
    for path in (DATASET / "val" / name).iterdir()
    if path.is_file()
}

assert actual_paths == expected_paths

assert Counter(
    item["true_id"] for item in verified
) == {0: 149, 1: 222}

print("Images verified:", len(verified))
print("Leaf groups verified:", len(groups["val"]))


# 4. VERIFY BOTH CHECKPOINTS

def load_verified_model(training):
    checkpoint = (
        ROOT / training["best_checkpoint"]
    ).resolve()

    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    if (
        sha256_file(checkpoint)
        != training["best_checkpoint_sha256"]
    ):
        raise ValueError(
            "Checkpoint SHA-256 mismatch."
        )

    model = YOLO(str(checkpoint))

    names = [
        model.names[i]
        for i in sorted(model.names)
    ]

    if names != CLASSES:
        raise ValueError(
            "Model class mapping mismatch."
        )

    return model


transfer_model = load_verified_model(
    transfer_training
)

baseline_model = load_verified_model(
    baseline_training
)


# 5. IDENTICAL INFERENCE PROCEDURE

device = (
    "0" if torch.cuda.is_available()
    else "cpu"
)

batch_size = 8


def evaluate(model, name):
    print(f"\nEvaluating {name}...")

    confusion = [[0, 0], [0, 0]]
    predictions = {}

    for start in range(
        0,
        len(verified),
        batch_size
    ):
        batch = verified[
            start:start + batch_size
        ]

        results = model.predict(
            source=[
                item["absolute_path"]
                for item in batch
            ],
            imgsz=224,
            batch=batch_size,
            device=device,
            verbose=False,
            save=False
        )

        if len(results) != len(batch):
            raise ValueError(
                "Prediction count mismatch."
            )

        for item, result in zip(
            batch,
            results
        ):
            if result.probs is None:
                raise ValueError(
                    "Missing classification output."
                )

            predicted = int(
                result.probs.top1
            )

            confidence = float(
                result.probs.top1conf
            )

            if (
                predicted not in (0, 1)
                or not math.isfinite(confidence)
                or not 0 <= confidence <= 1
            ):
                raise ValueError(
                    "Invalid model prediction."
                )

            confusion[
                item["true_id"]
            ][predicted] += 1

            predictions[item["path"]] = {
                "class_id": predicted,
                "confidence": confidence
            }

        print(
            name,
            min(start + batch_size, len(verified)),
            "/",
            len(verified)
        )

    return {
        "confusion": confusion,
        "metrics": calculate_metrics(confusion),
        "predictions": predictions
    }


transfer = evaluate(
    transfer_model,
    "TOMATO_TRANSFER"
)

baseline = evaluate(
    baseline_model,
    "GENERIC_BASELINE"
)


# 6. CHECK PREVIOUS TRANSFER RESULTS

previous_confusion = previous_validation[
    "confusion_matrix"
]["values"]

if transfer["confusion"] != previous_confusion:
    raise ValueError(
        "Transfer evaluation does not reproduce "
        "the previous confusion matrix. "
        "Review preprocessing and environment."
    )


# 7. PAIRED ERROR ANALYSIS

paired_rows = []

transfer_only_correct = 0
baseline_only_correct = 0
both_correct = 0
both_wrong = 0
different_predictions = 0

for item in verified:
    path = item["path"]
    true_id = item["true_id"]

    a = transfer["predictions"][path]
    b = baseline["predictions"][path]

    a_correct = a["class_id"] == true_id
    b_correct = b["class_id"] == true_id

    if a_correct and b_correct:
        both_correct += 1

    elif a_correct:
        transfer_only_correct += 1

    elif b_correct:
        baseline_only_correct += 1

    else:
        both_wrong += 1

    if a["class_id"] != b["class_id"]:
        different_predictions += 1

    paired_rows.append({
        "image": path,
        "leaf_group_id": item["leaf_group_id"],
        "true_class": CLASSES[true_id],
        "transfer_prediction":
            CLASSES[a["class_id"]],
        "transfer_confidence":
            a["confidence"],
        "baseline_prediction":
            CLASSES[b["class_id"]],
        "baseline_confidence":
            b["confidence"],
        "transfer_correct": a_correct,
        "baseline_correct": b_correct
    })


# 8. BUILD REPORTS

baseline_report = {
    "version": "1.0",
    "evaluation_split": "VALIDATION_ONLY",
    "checkpoint_sha256":
        baseline_training["best_checkpoint_sha256"],
    "split_manifest_sha256": split_hash,
    "validation_images": len(verified),
    "validation_leaf_groups": len(groups["val"]),
    "test_images_evaluated": 0,
    "confusion_matrix": {
        "class_order": CLASSES,
        "rows": "TRUE_LABEL",
        "columns": "PREDICTED_LABEL",
        "values": baseline["confusion"]
    },
    "metrics": baseline["metrics"],
    "real_greenhouse_validation": False,
    "water_stress_validated": False
}

comparison = {
    "version": "1.0",
    "generated_at_utc":
        datetime.now(timezone.utc).isoformat(),
    "task": "PEPPER_DISEASE_CLASSIFICATION",
    "comparison_split": "VALIDATION_ONLY",
    "validation_images": len(verified),
    "validation_leaf_groups": len(groups["val"]),
    "test_images_evaluated": 0,
    "split_manifest_sha256": split_hash,
    "transfer_checkpoint_sha256":
        transfer_training["best_checkpoint_sha256"],
    "baseline_checkpoint_sha256":
        baseline_training["best_checkpoint_sha256"],
    "transfer_metrics": transfer["metrics"],
    "baseline_metrics": baseline["metrics"],
    "transfer_confusion": transfer["confusion"],
    "baseline_confusion": baseline["confusion"],
    "paired_results": {
        "both_correct": both_correct,
        "transfer_only_correct":
            transfer_only_correct,
        "baseline_only_correct":
            baseline_only_correct,
        "both_wrong": both_wrong,
        "different_predictions":
            different_predictions
    },
    "observed_macro_f1_difference":
        transfer["metrics"]["macro_f1"]
        - baseline["metrics"]["macro_f1"],
    "causal_transfer_advantage_established":
        False,
    "real_greenhouse_generalization_verified":
        False,
    "water_stress_validated": False
}


# 9. SAVE RESULTS

REPORTS.mkdir(
    parents=True,
    exist_ok=True
)

BASELINE_OUTPUT.write_text(
    json.dumps(
        baseline_report,
        indent=2,
        allow_nan=False
    ) + "\n",
    encoding="utf-8"
)

COMPARISON_OUTPUT.write_text(
    json.dumps(
        comparison,
        indent=2,
        allow_nan=False
    ) + "\n",
    encoding="utf-8"
)

with PREDICTIONS_OUTPUT.open(
    "x",
    newline="",
    encoding="utf-8"
) as stream:
    writer = csv.DictWriter(
        stream,
        fieldnames=list(paired_rows[0])
    )
    writer.writeheader()
    writer.writerows(paired_rows)


# 10. PRINT RESULTS

print("\n" + "=" * 48)
print("PEPPER MODEL COMPARISON RESULTS")
print("=" * 48)

for label, result in (
    ("TOMATO TRANSFER", transfer),
    ("GENERIC BASELINE", baseline)
):
    metrics = result["metrics"]

    print("\n" + label)

    for name in (
        "accuracy",
        "balanced_accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1"
    ):
        print(
            name + ":",
            round(metrics[name], 4)
        )

    print("Confusion matrix:")

    for row in result["confusion"]:
        print(row)

print("\nPAIRED COMPARISON")
print("Both correct:", both_correct)
print(
    "Transfer only correct:",
    transfer_only_correct
)
print(
    "Baseline only correct:",
    baseline_only_correct
)
print("Both wrong:", both_wrong)

print(
    "Different predictions:",
    different_predictions
)

print("\nTest set: UNTOUCHED")
print("Real greenhouse validation: PENDING")
print("Water stress validation: PENDING")
print("Transfer advantage: NOT ESTABLISHED")

print("\nBaseline report:", BASELINE_OUTPUT)
print("Comparison report:", COMPARISON_OUTPUT)
print("Paired predictions:", PREDICTIONS_OUTPUT)

print("=" * 48)
print("PEPPER MODEL COMPARISON: PASS")

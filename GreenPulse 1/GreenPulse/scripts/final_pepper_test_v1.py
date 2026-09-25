
import csv
import hashlib
import json
import math
import os
import shutil
import tempfile

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]

REPORTS = ROOT / "reports"

SPLIT = REPORTS / "pepper_group_split_v1.json"

PROTOCOL = ROOT / (
    "configs/pepper_final_test_protocol_v1.json"
)

FREEZE = REPORTS / "pepper_candidate_freeze_v1.json"

TRAINING = (
    REPORTS / "pepper_transfer_training_v1.json"
)

VALIDATION = (
    REPORTS / "pepper_validation_evaluation_v1.json"
)

COMPARISON = (
    REPORTS / "pepper_model_comparison_v1.json"
)

ONNX_REPORT = (
    REPORTS / "pepper_onnx_parity_v1.json"
)

SOURCE = ROOT / (
    "datasets/external/"
    "plantvillage_pepper_source"
)

PROCESSED = ROOT / (
    "datasets/processed/"
    "pepper_cls_leafgroup_v1"
)

RELEASE = ROOT / (
    "models/release_candidates/pepper_transfer_v1"
)

FINAL_DIR = REPORTS / "pepper_final_test_v1"

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
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def metrics_from_confusion(matrix):
    per_class = {}

    for index, name in enumerate(CLASSES):

        tp = matrix[index][index]

        fn = sum(matrix[index]) - tp

        fp = sum(
            row[index]
            for row in matrix
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
            "f1": f1,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn
        }

    total = sum(
        sum(row)
        for row in matrix
    )

    correct = sum(
        matrix[i][i]
        for i in range(2)
    )

    return {
        "accuracy": correct / total,
        "balanced_accuracy": sum(
            x["recall"]
            for x in per_class.values()
        ) / 2,
        "macro_precision": sum(
            x["precision"]
            for x in per_class.values()
        ) / 2,
        "macro_recall": sum(
            x["recall"]
            for x in per_class.values()
        ) / 2,
        "macro_f1": sum(
            x["f1"]
            for x in per_class.values()
        ) / 2,
        "per_class": per_class
    }


print("=" * 48)
print("GREENPULSE PEPPER FINAL TEST")
print("=" * 48)


# =====================================
# 1. PREFLIGHT
# =====================================

if FINAL_DIR.exists():
    raise FileExistsError(
        "Final test results already exist. "
        "Do not repeat or overwrite the test."
    )

protocol = load_json(PROTOCOL)
freeze = load_json(FREEZE)
manifest = load_json(SPLIT)
training = load_json(TRAINING)

print("\nVerifying frozen experiment...")


# =====================================
# 2. VERIFY THE FREEZE RECORD
# =====================================

assert (
    freeze["final_test_status"]
    == "AUTHORIZED_NOT_EXECUTED"
)

assert (
    freeze["test_predictions_generated"]
    is False
)

assert (
    freeze["protocol_sha256"]
    == sha256_file(PROTOCOL)
)

assert (
    freeze["split_manifest_sha256"]
    == sha256_file(SPLIT)
)

assert (
    protocol["split_manifest_sha256"]
    == sha256_file(SPLIT)
)

assert (
    protocol["test_set_policy"]
    == "SINGLE_FINAL_EVALUATION"
)

assert (
    protocol["selected_model"]
    == "pepper_tomato_transfer_v1"
)

assert (
    protocol["selection_based_on_test_data"]
    is False
)

assert (
    protocol["inference"]["imgsz"]
    == 224
)

assert (
    protocol["inference"]["tta"]
    is False
)

evidence = {
    TRAINING: "training_report_sha256",
    VALIDATION: "validation_report_sha256",
    COMPARISON: "comparison_report_sha256",
    ONNX_REPORT: "onnx_report_sha256"
}

for path, field in evidence.items():
    if sha256_file(path) != freeze[field]:
        raise ValueError(
            f"Frozen evidence changed: {path}"
        )


# =====================================
# 3. VERIFY THE SELECTED MODEL
# =====================================

checkpoint = RELEASE / "pepper_transfer_v1.pt"

onnx_path = RELEASE / "pepper_transfer_v1.onnx"

assert checkpoint.is_file()
assert onnx_path.is_file()

checkpoint_hash = sha256_file(
    checkpoint
)

assert (
    checkpoint_hash
    == freeze["pytorch_sha256"]
)

assert (
    checkpoint_hash
    == protocol["selected_checkpoint_sha256"]
)

assert (
    checkpoint_hash
    == training["best_checkpoint_sha256"]
)

assert (
    sha256_file(onnx_path)
    == freeze["onnx_sha256"]
)

print("Frozen PyTorch model: VERIFIED")
print("ONNX artifact: VERIFIED")


# =====================================
# 4. VERIFY TEST ISOLATION
# =====================================

if (PROCESSED / "test").exists():
    raise ValueError(
        "Unexpected test directory "
        "inside training dataset."
    )

groups = {
    name: set()
    for name in ("train", "val", "test")
}

hashes = {
    name: set()
    for name in ("train", "val", "test")
}

for item in manifest["samples"]:

    partition = item["split"]

    if partition not in groups:
        raise ValueError(
            "Unknown dataset partition."
        )

    groups[partition].add(
        item["leaf_group_id"]
    )

    hashes[partition].add(
        item["sha256"]
    )

for first, second in (
    ("train", "val"),
    ("train", "test"),
    ("val", "test")
):
    assert groups[first].isdisjoint(
        groups[second]
    )

    assert hashes[first].isdisjoint(
        hashes[second]
    )


# =====================================
# 5. RECONSTRUCT THE FROZEN TEST SET
# =====================================

test_samples = sorted(
    (
        item
        for item in manifest["samples"]
        if item["split"] == "test"
    ),
    key=lambda item: item["path"]
)

assert len(test_samples) == 371
assert len(groups["test"]) == 51

frozen_test_manifest = [
    {
        "path": item["path"],
        "class_name": (
            CLASSES[
                CLASS_MAPPING[item["class_name"]]
            ]
        ),
        "leaf_group_id": item["leaf_group_id"],
        "sha256": item["sha256"]
    }
    for item in test_samples
]

manifest_hash = hashlib.sha256(
    json.dumps(
        frozen_test_manifest,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")
).hexdigest()

assert (
    manifest_hash
    == freeze["test_sample_manifest_sha256"]
)

assert (
    manifest_hash
    == protocol["test_sample_manifest_sha256"]
)


# =====================================
# 6. VERIFY ALL TEST IMAGE BYTES
# =====================================

verified = []

source_root = SOURCE.resolve()

seen_paths = set()

print("\nVerifying reserved test images...")

for item in test_samples:

    image = (
        SOURCE / item["path"]
    ).resolve()

    if not image.is_relative_to(
        source_root
    ):
        raise ValueError(
            "Unsafe test image path."
        )

    if not image.is_file():
        raise FileNotFoundError(image)

    if sha256_file(image) != item["sha256"]:
        raise ValueError(
            "Test image integrity failure."
        )

    key = str(image).casefold()

    if key in seen_paths:
        raise ValueError(
            "Duplicate test image path."
        )

    seen_paths.add(key)

    verified.append({
        "path": item["path"],
        "absolute_path": str(image),
        "sha256": item["sha256"],
        "leaf_group_id": item["leaf_group_id"],
        "true_id": CLASS_MAPPING[
            item["class_name"]
        ]
    })

assert Counter(
    item["true_id"]
    for item in verified
) == {0: 149, 1: 222}

print("Test images: 371")
print("Test leaf groups: 51")
print("Source integrity: PASS")
print("Known group overlap: NONE")
print("Exact image overlap: NONE")


# =====================================
# 7. LOAD FROZEN MODEL
# =====================================

model = YOLO(
    str(checkpoint)
)

actual_classes = [
    model.names[i]
    for i in sorted(model.names)
]

assert actual_classes == CLASSES

# Fixed evaluation device.
device = "cpu"
batch_size = 8

print("\nStarting final test evaluation...")
print("Device:", device)


# =====================================
# 8. ONE-TIME TEST INFERENCE
# =====================================

confusion = [
    [0, 0],
    [0, 0]
]

predictions = []
errors = []

groups_with_errors = set()

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
        augment=False,
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

        probabilities = [
            float(value)
            for value in (
                result.probs.data.tolist()
            )
        ]

        if (
            len(probabilities) != 2
            or not all(
                math.isfinite(p)
                and 0 <= p <= 1
                for p in probabilities
            )
        ):
            raise ValueError(
                "Invalid model probabilities."
            )

        predicted = max(
            range(2),
            key=lambda i: probabilities[i]
        )

        true_id = item["true_id"]

        confidence = probabilities[
            predicted
        ]

        confusion[
            true_id
        ][
            predicted
        ] += 1

        row = {
            "image_path": item["path"],
            "image_sha256": item["sha256"],
            "leaf_group_id": item["leaf_group_id"],
            "true_class": CLASSES[true_id],
            "predicted_class":
                CLASSES[predicted],
            "confidence": confidence,
            "correct": predicted == true_id
        }

        predictions.append(row)

        if predicted != true_id:
            errors.append(row)
            groups_with_errors.add(
                item["leaf_group_id"]
            )

    print(
        "Evaluated:",
        min(
            start + batch_size,
            len(verified)
        ),
        "/371"
    )


# =====================================
# 9. CALCULATE PREDECLARED METRICS
# =====================================

metrics = metrics_from_confusion(
    confusion
)

report = {
    "report_version": "1.0",
    "evaluated_at_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),
    "project": "GreenPulse",
    "crop": "bell_pepper",
    "task": "DISEASE_CLASSIFICATION",
    "evaluation_split": "FROZEN_FINAL_TEST",
    "selected_model":
        "pepper_tomato_transfer_v1",
    "checkpoint_sha256": checkpoint_hash,
    "protocol_sha256":
        sha256_file(PROTOCOL),
    "freeze_record_sha256":
        sha256_file(FREEZE),
    "split_manifest_sha256":
        sha256_file(SPLIT),
    "test_sample_manifest_sha256":
        manifest_hash,
    "evaluated_images":
        len(predictions),
    "claimed_leaf_groups":
        len(groups["test"]),
    "confusion_matrix": {
        "class_order": CLASSES,
        "rows": "TRUE_LABEL",
        "columns": "PREDICTED_LABEL",
        "values": confusion
    },
    "metrics": metrics,
    "error_analysis": {
        "total_errors": len(errors),
        "leaf_groups_with_errors":
            len(groups_with_errors),
        "high_confidence_errors_0_90":
            sum(
                row["confidence"] >= 0.90
                for row in errors
            )
    },
    "test_used_for_model_selection":
        False,
    "transfer_advantage_established":
        False,
    "physical_plant_identity_verified":
        False,
    "independent_greenhouse_validation":
        False,
    "water_stress_model_validated":
        False,
    "hailo_deployment_validated":
        False,
    "physical_actuation_authorized":
        False,
    "limitation": (
        "PlantVillage test evaluation "
        "with claimed leaf-group separation. "
        "Not independent real-greenhouse "
        "or verified physical-plant validation."
    )
}


# =====================================
# 10. ATOMIC RESULT PUBLICATION
# =====================================

REPORTS.mkdir(
    parents=True,
    exist_ok=True
)

temporary_dir = Path(
    tempfile.mkdtemp(
        prefix=".pepper-final-temp-",
        dir=REPORTS
    )
)

try:

    report_path = (
        temporary_dir /
        "final_test_report.json"
    )

    predictions_path = (
        temporary_dir /
        "predictions.csv"
    )

    errors_path = (
        temporary_dir /
        "errors.csv"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            allow_nan=False
        ) + "\n",
        encoding="utf-8"
    )

    fields = [
        "image_path",
        "image_sha256",
        "leaf_group_id",
        "true_class",
        "predicted_class",
        "confidence",
        "correct"
    ]

    for path, rows in (
        (predictions_path, predictions),
        (errors_path, errors)
    ):

        with path.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as stream:

            writer = csv.DictWriter(
                stream,
                fieldnames=fields
            )

            writer.writeheader()
            writer.writerows(rows)

    if FINAL_DIR.exists():
        raise FileExistsError(
            "Final test results already exist."
        )

    temporary_dir.rename(
        FINAL_DIR
    )

finally:

    if temporary_dir.exists():
        shutil.rmtree(
            temporary_dir
        )


# =====================================
# 11. PRINT FINAL RESULTS
# =====================================

print("\n" + "=" * 48)
print("GREENPULSE PEPPER FINAL TEST RESULTS")
print("=" * 48)

print(
    "Accuracy:",
    round(metrics["accuracy"], 4)
)

print(
    "Balanced accuracy:",
    round(
        metrics["balanced_accuracy"],
        4
    )
)

print(
    "Macro precision:",
    round(
        metrics["macro_precision"],
        4
    )
)

print(
    "Macro recall:",
    round(
        metrics["macro_recall"],
        4
    )
)

print(
    "Macro F1:",
    round(metrics["macro_f1"], 4)
)

print("\nCONFUSION MATRIX")

for row in confusion:
    print(row)

print("\nPER-CLASS METRICS")

for name, values in (
    metrics["per_class"].items()
):

    print(
        name,
        "| Precision:",
        round(values["precision"], 4),
        "| Recall:",
        round(values["recall"], 4),
        "| F1:",
        round(values["f1"], 4)
    )

print("\nTotal errors:", len(errors))

print(
    "Leaf groups with errors:",
    len(groups_with_errors)
)

print("\nFinal test: COMPLETED")
print("Test-driven model changes: NOT ALLOWED")
print("Real greenhouse validation: PENDING")
print("Water stress validation: PENDING")
print("Physical actuation: DISABLED")

print("\nResults:", FINAL_DIR)

print("=" * 48)
print("PEPPER FINAL TEST: COMPLETE")

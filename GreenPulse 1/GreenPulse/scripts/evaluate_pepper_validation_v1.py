
import csv
import hashlib
import json
import statistics

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import torch

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]

TRAINING_REPORT = ROOT / (
    "reports/pepper_transfer_training_v1.json"
)

SPLIT = ROOT / (
    "reports/pepper_group_split_v1.json"
)

BUILD_REPORT = ROOT / (
    "reports/pepper_training_dataset_v1.json"
)

DATASET = ROOT / (
    "datasets/processed/pepper_cls_leafgroup_v1"
)

OUTPUT = ROOT / (
    "reports/pepper_validation_evaluation_v1.json"
)

ERRORS = ROOT / (
    "reports/pepper_validation_errors_v1.csv"
)

CLASSES = [
    "bacterial_spot",
    "healthy"
]

CLASS_MAPPING = {
    "Pepper,_bell___Bacterial_spot":
        "bacterial_spot",
    "Pepper,_bell___healthy":
        "healthy"
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


def safe_divide(a, b):
    return a / b if b else 0.0


def calculate_metrics(confusion):

    per_class = {}

    for index, name in enumerate(CLASSES):

        tp = confusion[index][index]

        fn = sum(
            confusion[index]
        ) - tp

        fp = sum(
            row[index]
            for row in confusion
        ) - tp

        support = tp + fn

        precision = safe_divide(
            tp, tp + fp
        )

        recall = safe_divide(
            tp, support
        )

        f1 = safe_divide(
            2 * precision * recall,
            precision + recall
        )

        per_class[name] = {
            "support": support,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    correct = sum(
        confusion[i][i]
        for i in range(len(CLASSES))
    )

    total = sum(
        sum(row)
        for row in confusion
    )

    return {
        "accuracy": safe_divide(
            correct, total
        ),

        "balanced_accuracy":
            statistics.mean(
                item["recall"]
                for item in per_class.values()
            ),

        "macro_precision":
            statistics.mean(
                item["precision"]
                for item in per_class.values()
            ),

        "macro_recall":
            statistics.mean(
                item["recall"]
                for item in per_class.values()
            ),

        "macro_f1":
            statistics.mean(
                item["f1"]
                for item in per_class.values()
            ),

        "per_class": per_class
    }


def main():

    print("=" * 48)
    print("GREENPULSE PEPPER VALIDATION")
    print("=" * 48)

    # 1. PREFLIGHT

    for path in (
        TRAINING_REPORT,
        SPLIT,
        BUILD_REPORT
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    if OUTPUT.exists() or ERRORS.exists():
        raise FileExistsError(
            "Evaluation output already exists. "
            "Nothing overwritten."
        )

    training = json.loads(
        TRAINING_REPORT.read_text(
            encoding="utf-8-sig"
        )
    )

    manifest = json.loads(
        SPLIT.read_text(
            encoding="utf-8-sig"
        )
    )

    build = json.loads(
        BUILD_REPORT.read_text(
            encoding="utf-8-sig"
        )
    )

    assert training["training_completed"] is True

    assert (
        training["test_evaluation_completed"]
        is False
    )

    assert (
        build["split_manifest_sha256"]
        == sha256_file(SPLIT)
    )

    assert build["test_copied"] is False

    assert not (
        DATASET / "test"
    ).exists()

    # 2. VERIFY TRAINED MODEL

    checkpoint = (
        ROOT / training["best_checkpoint"]
    ).resolve()

    if not checkpoint.is_file():
        raise FileNotFoundError(
            "Trained checkpoint missing."
        )

    if (
        sha256_file(checkpoint)
        != training["best_checkpoint_sha256"]
    ):
        raise ValueError(
            "Trained checkpoint integrity failure."
        )

    model = YOLO(
        str(checkpoint)
    )

    names = model.names

    actual_names = [
        names[i]
        for i in sorted(names)
    ]

    if actual_names != CLASSES:
        raise ValueError(
            "Model class mapping mismatch."
        )

    # 3. VERIFY VALIDATION DATA

    print(
        "\nVerifying validation dataset..."
    )

    records = [
        item
        for item in manifest["samples"]
        if item["split"] == "val"
    ]

    if len(records) != 371:
        raise ValueError(
            "Unexpected validation image count."
        )

    group_sets = {
        partition: {
            item["leaf_group_id"]
            for item in manifest["samples"]
            if item["split"] == partition
        }
        for partition in (
            "train", "val", "test"
        )
    }

    assert group_sets["val"].isdisjoint(
        group_sets["train"]
    )

    assert group_sets["val"].isdisjoint(
        group_sets["test"]
    )

    if len(group_sets["val"]) != 51:
        raise ValueError(
            "Unexpected validation group count."
        )

    verified = []

    expected_files = set()

    for item in records:

        class_name = CLASS_MAPPING[
            item["class_name"]
        ]

        image = (
            DATASET /
            "val" /
            class_name /
            Path(item["path"]).name
        ).resolve()

        if not image.is_relative_to(
            DATASET.resolve()
        ):
            raise ValueError(
                "Unsafe validation path."
            )

        if not image.is_file():
            raise FileNotFoundError(image)

        if (
            sha256_file(image)
            != item["sha256"]
        ):
            raise ValueError(
                "Validation image hash mismatch."
            )

        key = str(image).casefold()

        if key in expected_files:
            raise ValueError(
                "Duplicate validation filename."
            )

        expected_files.add(key)

        verified.append({
            **item,
            "absolute_path": str(image),
            "true_label": CLASSES.index(
                class_name
            )
        })

    actual_files = {
        str(path.resolve()).casefold()
        for class_name in CLASSES
        for path in (
            DATASET / "val" / class_name
        ).iterdir()
        if path.is_file()
    }

    if actual_files != expected_files:
        raise ValueError(
            "Unexpected validation files."
        )

    print(
        "Validation images:",
        len(verified)
    )

    print(
        "Validation leaf groups:",
        len(group_sets["val"])
    )

    print(
        "Test dataset: RESERVED"
    )

    # 4. MODEL INFERENCE

    device = (
        "0"
        if torch.cuda.is_available()
        else "cpu"
    )

    batch_size = (
        16
        if device != "cpu"
        else 8
    )

    print("\nRunning model inference...")
    print("Device:", device)

    confusion = [
        [0, 0],
        [0, 0]
    ]

    mistakes = []
    correct_confidences = []

    group_results = Counter()

    for start in range(
        0,
        len(verified),
        batch_size
    ):

        batch = verified[
            start:start + batch_size
        ]

        predictions = model.predict(
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

        if len(predictions) != len(batch):
            raise ValueError(
                "Prediction count mismatch."
            )

        for item, result in zip(
            batch,
            predictions
        ):

            if result.probs is None:
                raise ValueError(
                    "Classification output missing."
                )

            true_id = item["true_label"]

            predicted_id = int(
                result.probs.top1
            )

            confidence = float(
                result.probs.top1conf
            )

            if predicted_id not in (0, 1):
                raise ValueError(
                    "Unexpected predicted class."
                )

            confusion[
                true_id
            ][
                predicted_id
            ] += 1

            group_id = item[
                "leaf_group_id"
            ]

            group_results[
                (group_id, "total")
            ] += 1

            if predicted_id == true_id:

                correct_confidences.append(
                    confidence
                )

                group_results[
                    (group_id, "correct")
                ] += 1

            else:

                mistakes.append({
                    "path": item["path"],
                    "leaf_group_id": group_id,
                    "true_class":
                        CLASSES[true_id],
                    "predicted_class":
                        CLASSES[predicted_id],
                    "confidence":
                        confidence
                })

        print(
            "Evaluated:",
            min(
                start + batch_size,
                len(verified)
            ),
            "/",
            len(verified)
        )

    # 5. CALCULATE METRICS

    metrics = calculate_metrics(
        confusion
    )

    errors_by_class = Counter(
        item["true_class"]
        for item in mistakes
    )

    groups_with_errors = {
        item["leaf_group_id"]
        for item in mistakes
    }

    high_confidence_errors = sum(
        item["confidence"] >= 0.90
        for item in mistakes
    )

    # 6. CREATE REPORT

    report = {
        "version": "1.0",
        "generated_at_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "project": "GreenPulse",

        "task":
            "PEPPER_DISEASE_CLASSIFICATION",

        "evaluation_split":
            "VALIDATION_ONLY",

        "checkpoint_sha256":
            sha256_file(checkpoint),

        "split_manifest_sha256":
            sha256_file(SPLIT),

        "validation_images":
            len(verified),

        "validation_leaf_groups":
            len(group_sets["val"]),

        "test_images_evaluated": 0,

        "confusion_matrix": {
            "class_order": CLASSES,
            "rows": "TRUE_LABEL",
            "columns": "PREDICTED_LABEL",
            "values": confusion
        },

        "metrics": metrics,

        "error_analysis": {
            "total_errors":
                len(mistakes),

            "errors_by_true_class":
                dict(errors_by_class),

            "leaf_groups_with_errors":
                len(groups_with_errors),

            "high_confidence_errors_0_90":
                high_confidence_errors,

            "mean_correct_prediction_confidence":
                statistics.mean(
                    correct_confidences
                )
                if correct_confidences
                else None
        },

        "limitations": {
            "controlled_dataset":
                "PLANTVILLAGE",

            "physical_plant_identity_verified":
                False,

            "real_greenhouse_validation":
                False,

            "water_stress_model_trained":
                False,

            "confidence_calibrated":
                False,

            "transfer_advantage_verified":
                False
        }
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Write error CSV and report only after
    # all validation predictions succeed.

    with ERRORS.open(
        "x",
        newline="",
        encoding="utf-8"
    ) as stream:

        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "path",
                "leaf_group_id",
                "true_class",
                "predicted_class",
                "confidence"
            ]
        )

        writer.writeheader()
        writer.writerows(mistakes)

    OUTPUT.write_text(
        json.dumps(
            report,
            indent=2,
            allow_nan=False
        ) + "\n",
        encoding="utf-8"
    )

    # 7. PRINT RESULTS

    print("\n" + "=" * 48)
    print("PEPPER VALIDATION RESULTS")
    print("=" * 48)

    for name in (
        "accuracy",
        "balanced_accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1"
    ):

        print(
            name + ":",
            round(
                metrics[name],
                4
            )
        )

    print("\nCONFUSION MATRIX")
    print("Class order:", CLASSES)

    for row in confusion:
        print(row)

    print("\nPER-CLASS METRICS")

    for name, values in (
        metrics["per_class"].items()
    ):

        print(
            name,
            "| Precision:",
            round(
                values["precision"], 4
            ),
            "| Recall:",
            round(
                values["recall"], 4
            ),
            "| F1:",
            round(
                values["f1"], 4
            )
        )

    print(
        "\nTotal errors:",
        len(mistakes)
    )

    print(
        "Leaf groups with errors:",
        len(groups_with_errors)
    )

    print(
        "High-confidence errors:",
        high_confidence_errors
    )

    print("\nReport:", OUTPUT)
    print("Error analysis:", ERRORS)

    print("\nTEST SET: UNTOUCHED")
    print("REAL GREENHOUSE VALIDATION: PENDING")
    print("WATER STRESS VALIDATION: PENDING")

    print("=" * 48)
    print("PEPPER VALIDATION: PASS")


if __name__ == "__main__":
    main()

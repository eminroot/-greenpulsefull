import csv
import json
import hashlib
import torch

from pathlib import Path
from ultralytics import YOLO
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix
)

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

torch.set_num_threads(12)

MODEL_PATH = Path(
    "models/greenpulse_tomato_yolo11n_cls_v1.0.pt"
)

TEST_DIR = Path(
    "datasets/processed/tomato_cls/test"
)

MANIFEST = Path(
    "reports/tomato_split_v1/test.csv"
)

REGISTRY = Path(
    "reports/model_registry.json"
)

OUTPUT = Path("reports/tomato_evaluation_v1")
OUTPUT.mkdir(parents=True, exist_ok=True)

def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()

registry = json.loads(
    REGISTRY.read_text(encoding="utf-8")
)

assert sha256(MODEL_PATH) == registry["model_sha256"], \
    "MODEL HASH MISMATCH!"

assert sha256(MANIFEST) == \
    registry["dataset_manifest_sha256"]["test"], \
    "TEST MANIFEST HASH MISMATCH!"

model = YOLO(str(MODEL_PATH))

names = model.names

classes = [
    names[i] for i in sorted(names)
]

assert len(classes) == 10

class_to_id = {
    name: i for i, name in enumerate(classes)
}

images = []
y_true = []

with open(MANIFEST, encoding="utf-8") as f:
    for row in csv.DictReader(f):

        category = row["class_name"]

        path = (
            TEST_DIR
            / category
            / Path(row["image_path"]).name
        )

        if not path.is_file():
            raise FileNotFoundError(path)

        images.append(str(path))
        y_true.append(class_to_id[category])

assert len(images) == 3639

print("\nGREENPULSE INDEPENDENT TEST")
print("--------------------------------")
print("MODEL VERIFIED")
print("TEST MANIFEST VERIFIED")
print("TEST IMAGES:", len(images))
print("DEVICE: CPU")
print("--------------------------------")

y_pred = []
top5_correct = 0
predictions = []

BATCH_SIZE = 32

for start in range(
    0,
    len(images),
    BATCH_SIZE
):

    batch = images[
        start:start + BATCH_SIZE
    ]

    results = model.predict(
        source=batch,
        imgsz=224,
        batch=BATCH_SIZE,
        device="cpu",
        verbose=False
    )

    for result in results:

        predicted_id = int(
            result.probs.top1
        )

        confidence = float(
            result.probs.top1conf.item()
        )

        actual_class = Path(
            result.path
        ).parent.name

        actual_id = class_to_id[
            actual_class
        ]

        top5 = [
            int(x)
            for x in result.probs.top5
        ]

        top5_correct += (
            actual_id in top5
        )

        y_pred.append(predicted_id)

        predictions.append({
            "image": str(result.path),
            "actual": actual_class,
            "predicted": classes[predicted_id],
            "confidence": confidence,
            "correct": actual_id == predicted_id
        })

    print(
        "Evaluated:",
        min(start + BATCH_SIZE, len(images)),
        "/",
        len(images)
    )

# Actual labels are also reconstructed from the
# returned image paths to ensure correct alignment.

y_true = [
    class_to_id[Path(p["image"]).parent.name]
    for p in predictions
]

assert len(y_true) == len(y_pred) == 3639

accuracy = accuracy_score(
    y_true,
    y_pred
)

balanced_accuracy = balanced_accuracy_score(
    y_true,
    y_pred
)

report = classification_report(
    y_true,
    y_pred,
    labels=list(range(10)),
    target_names=classes,
    output_dict=True,
    zero_division=0
)

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=list(range(10))
)

healthy_id = class_to_id[
    "Tomato___healthy"
]

dangerous_errors = [
    p for p in predictions
    if p["actual"] != "Tomato___healthy"
    and p["predicted"] == "Tomato___healthy"
]

# Save individual predictions

with open(
    OUTPUT / "predictions.csv",
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "image",
            "actual",
            "predicted",
            "confidence",
            "correct"
        ]
    )

    writer.writeheader()
    writer.writerows(predictions)

# Save dangerous classification errors

with open(
    OUTPUT / "disease_as_healthy_errors.csv",
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "image",
            "actual",
            "predicted",
            "confidence",
            "correct"
        ]
    )

    writer.writeheader()
    writer.writerows(dangerous_errors)

# Save evaluation report

summary = {
    "model_sha256": sha256(MODEL_PATH),
    "test_manifest_sha256": sha256(MANIFEST),
    "test_images": len(images),
    "accuracy": accuracy,
    "balanced_accuracy": balanced_accuracy,
    "top5_accuracy": top5_correct / len(images),
    "macro_precision": report["macro avg"]["precision"],
    "macro_recall": report["macro avg"]["recall"],
    "macro_f1": report["macro avg"]["f1-score"],
    "disease_as_healthy_errors": len(dangerous_errors),
    "classification_report": report,
    "limitations": [
        "PlantVillage domain",
        "1348 test images have unverified leaf grouping",
        "Real greenhouse performance not established",
        "Water stress detection not evaluated"
    ]
}

(OUTPUT / "evaluation.json").write_text(
    json.dumps(summary, indent=4),
    encoding="utf-8"
)

# Confusion matrix

fig, ax = plt.subplots(
    figsize=(13, 11)
)

im = ax.imshow(cm, cmap="Blues")

ax.set_xticks(range(10))
ax.set_yticks(range(10))

ax.set_xticklabels(
    classes,
    rotation=90,
    fontsize=8
)

ax.set_yticklabels(
    classes,
    fontsize=8
)

ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_title(
    "GreenPulse Tomato Classification - TEST"
)

fig.colorbar(im, ax=ax)

plt.tight_layout()

plt.savefig(
    OUTPUT / "confusion_matrix.png",
    dpi=200
)

plt.close()

print("\nGREENPULSE FINAL TEST EVALUATION")
print("--------------------------------")

print("Accuracy:", round(accuracy, 4))

print(
    "Balanced Accuracy:",
    round(balanced_accuracy, 4)
)

print(
    "Macro Precision:",
    round(report["macro avg"]["precision"], 4)
)

print(
    "Macro Recall:",
    round(report["macro avg"]["recall"], 4)
)

print(
    "Macro F1:",
    round(report["macro avg"]["f1-score"], 4)
)

print(
    "Disease classified as healthy:",
    len(dangerous_errors)
)

print("--------------------------------")
print("REPORTS SAVED:", OUTPUT)

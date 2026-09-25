import csv
import json
import hashlib
from pathlib import Path
from collections import defaultdict

import numpy as np
import torch
import onnxruntime as ort
from ultralytics import YOLO

torch.set_num_threads(12)

PT = Path("models/greenpulse_tomato_yolo11n_cls_v1.0.pt")
ONNX = Path("models/greenpulse_tomato_yolo11n_cls_v1.0.onnx")
MANIFEST = Path("reports/tomato_split_v1/validation.csv")
REGISTRY = Path("reports/model_registry.json")

OUTPUT = Path("reports/tomato_parity_v1")
OUTPUT.mkdir(parents=True, exist_ok=True)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

assert sha256(PT) == registry["model_sha256"]
assert sha256(MANIFEST) == registry["dataset_manifest_sha256"]["validation"]

if "CPUExecutionProvider" not in ort.get_available_providers():
    raise RuntimeError("ONNX Runtime CPU provider unavailable")

groups = defaultdict(list)

with open(MANIFEST, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        groups[row["class_name"]].append(row["image_path"])

images = []

for category in sorted(groups):
    selected = sorted(groups[category])[:5]

    if len(selected) != 5:
        raise RuntimeError(f"Insufficient images: {category}")

    images.extend(selected)

assert len(images) == 50

print("\nGREENPULSE MODEL PARITY TEST")
print("--------------------------------")
print("PyTorch:", PT)
print("ONNX:", ONNX)
print("Images:", len(images))
print("Execution: CPU")
print("--------------------------------")

pt_model = YOLO(str(PT))
onnx_model = YOLO(str(ONNX))

assert pt_model.names == onnx_model.names, \
    "Model class mappings differ!"

rows = []
differences = []
agreements = 0

for index, image in enumerate(images, 1):

    pt_result = pt_model.predict(
        source=image,
        imgsz=224,
        device="cpu",
        verbose=False
    )[0]

    onnx_result = onnx_model.predict(
        source=image,
        imgsz=224,
        device="cpu",
        verbose=False
    )[0]

    pt_probs = pt_result.probs.data.cpu().numpy()
    onnx_probs = onnx_result.probs.data.cpu().numpy()

    if pt_probs.shape != onnx_probs.shape:
        raise RuntimeError("Output shapes differ!")

    difference = float(
        np.max(np.abs(pt_probs - onnx_probs))
    )

    pt_class = int(np.argmax(pt_probs))
    onnx_class = int(np.argmax(onnx_probs))

    agreement = pt_class == onnx_class

    differences.append(difference)
    agreements += int(agreement)

    rows.append({
        "image": image,
        "pt_class": pt_model.names[pt_class],
        "onnx_class": onnx_model.names[onnx_class],
        "agreement": agreement,
        "max_probability_difference": difference
    })

    print(f"Checked: {index}/50")

with open(
    OUTPUT / "parity_predictions.csv",
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(rows[0].keys())
    )

    writer.writeheader()
    writer.writerows(rows)

maximum_difference = max(differences)
mean_difference = float(np.mean(differences))
agreement_rate = agreements / len(images)

status = (
    "PASS"
    if agreement_rate == 1.0
    and maximum_difference < 0.01
    else "REVIEW_REQUIRED"
)

report = {
    "pt_sha256": sha256(PT),
    "onnx_sha256": sha256(ONNX),
    "validation_manifest_sha256": sha256(MANIFEST),
    "images_tested": len(images),
    "agreement_rate": agreement_rate,
    "mean_probability_difference": mean_difference,
    "maximum_probability_difference": maximum_difference,
    "status": status
}

(OUTPUT / "parity_report.json").write_text(
    json.dumps(report, indent=4),
    encoding="utf-8"
)

print("\nGREENPULSE PARITY RESULTS")
print("--------------------------------")
print("Images:", len(images))
print("Matching predictions:", agreements)
print("Agreement:", f"{agreement_rate:.2%}")
print("Mean difference:", round(mean_difference, 8))
print("Maximum difference:", round(maximum_difference, 8))
print("STATUS:", status)
print("--------------------------------")

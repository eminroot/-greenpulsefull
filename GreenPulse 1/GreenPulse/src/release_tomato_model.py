import json
import hashlib
from pathlib import Path
from ultralytics import YOLO

MODEL = Path("models/greenpulse_tomato_yolo11n_cls_v1.0.pt")
ONNX = MODEL.with_suffix(".onnx")

EVALUATION = Path("reports/tomato_evaluation_v1/evaluation.json")
PARITY = Path("reports/tomato_parity_v1/parity_report.json")
REGISTRY = Path("reports/model_registry.json")

OUTPUT = Path("models/tomato_v1_release.json")

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for path in [MODEL, ONNX, EVALUATION, PARITY, REGISTRY]:
    if not path.is_file():
        raise FileNotFoundError(path)

evaluation = json.loads(EVALUATION.read_text(encoding="utf-8"))
parity = json.loads(PARITY.read_text(encoding="utf-8"))
registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

assert sha256(MODEL) == registry["model_sha256"]
assert sha256(ONNX) == parity["onnx_sha256"]
assert sha256(MODEL) == parity["pt_sha256"]
assert parity["status"] == "PASS"
assert parity["agreement_rate"] == 1.0
assert evaluation["test_images"] == 3639
assert evaluation["model_sha256"] == sha256(MODEL)

model = YOLO(str(MODEL))
classes = [model.names[i] for i in sorted(model.names)]

release = {
    "project": "GreenPulse",
    "version": "1.0",
    "model": "YOLO11n Classification",
    "crop_scope": "tomato",
    "task": "leaf_disease_classification",
    "input_size": [224, 224],
    "classes": classes,
    "pytorch": {
        "file": str(MODEL),
        "sha256": sha256(MODEL)
    },
    "onnx": {
        "file": str(ONNX),
        "sha256": sha256(ONNX)
    },
    "test_results": {
        "images": evaluation["test_images"],
        "accuracy": evaluation["accuracy"],
        "macro_f1": evaluation["macro_f1"]
    },
    "onnx_parity": {
        "status": parity["status"],
        "agreement": parity["agreement_rate"],
        "maximum_difference": parity["maximum_probability_difference"]
    },
    "deployment": {
        "hailo_validation": "PENDING",
        "edge_ram_validation": "PENDING",
        "autonomous_irrigation": "DISABLED"
    },
    "limitations": [
        "Public dataset benchmark only",
        "Real greenhouse validation pending",
        "Early water stress detection not validated",
        "Some physical leaf identities remain unverified",
        "Dataset licensing review required before distribution"
    ]
}

if OUTPUT.exists():
    raise RuntimeError("Release already exists. Refusing to overwrite.")

OUTPUT.write_text(
    json.dumps(release, indent=4),
    encoding="utf-8"
)

print("\nGREENPULSE MODEL RELEASE")
print("--------------------------------")
print("MODEL: YOLO11n Classification")
print("CLASSES:", len(classes))
print("TEST ACCURACY:", round(evaluation["accuracy"], 4))
print("ONNX PARITY:", parity["status"])
print("RELEASE:", OUTPUT)
print("--------------------------------")
print("RELEASE PACKAGE CREATED!")

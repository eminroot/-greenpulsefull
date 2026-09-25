from pathlib import Path
import hashlib
import shutil
import json
import torch
import ultralytics
from datetime import datetime, timezone

SOURCE = Path(
    "runs/greenpulse/tomato_cpu_v1/weights/best.pt"
)

DESTINATION = Path(
    "models/greenpulse_tomato_yolo11n_cls_v1.0.pt"
)

REGISTRY = Path("reports/model_registry.json")

def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()

if not SOURCE.is_file():
    raise FileNotFoundError(SOURCE)

if DESTINATION.exists() or REGISTRY.exists():
    raise RuntimeError(
        "Model already registered. Existing release will not be overwritten."
    )

DESTINATION.parent.mkdir(parents=True, exist_ok=True)
REGISTRY.parent.mkdir(parents=True, exist_ok=True)

shutil.copy2(SOURCE, DESTINATION)

manifests = {}

for split in ["train", "validation", "test"]:
    path = Path(f"reports/tomato_split_v1/{split}.csv")

    if not path.is_file():
        raise FileNotFoundError(path)

    manifests[split] = sha256(path)

registry = {
    "project": "GreenPulse",
    "model_name": "YOLO11n Classification",
    "version": "1.0",
    "crop": "tomato",
    "classes": 10,
    "status": "VALIDATION_COMPLETE_TEST_PENDING",
    "training_device": "CPU",
    "epochs_configured": 15,
    "image_size": 224,
    "validation_top1": 0.996,
    "pytorch_version": torch.__version__,
    "ultralytics_version": ultralytics.__version__,
    "model_path": str(DESTINATION),
    "model_sha256": sha256(DESTINATION),
    "dataset_manifest_sha256": manifests,
    "registered_at": datetime.now(timezone.utc).isoformat()
}

REGISTRY.write_text(
    json.dumps(registry, indent=4),
    encoding="utf-8"
)

print("\nGREENPULSE MODEL REGISTRATION")
print("--------------------------------")
print("MODEL:", DESTINATION)
print("VERSION: 1.0")
print("STATUS: VALIDATION COMPLETE")
print("MODEL SHA256:", registry["model_sha256"])
print("REGISTRY:", REGISTRY)
print("--------------------------------")
print("MODEL SUCCESSFULLY REGISTERED!")

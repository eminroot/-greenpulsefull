from ultralytics import YOLO
from pathlib import Path
import onnx
import hashlib
import json

MODEL = Path(
    "models/greenpulse_tomato_yolo11n_cls_v1.0.pt"
)

REGISTRY = Path("reports/model_registry.json")

EXPECTED = MODEL.with_suffix(".onnx")

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

assert MODEL.is_file()
assert sha256(MODEL) == registry["model_sha256"]

if EXPECTED.exists():
    raise RuntimeError(
        "ONNX file already exists. "
        "Existing artifact will not be overwritten."
    )

print("\nGREENPULSE ONNX EXPORT")
print("-----------------------------")

model = YOLO(str(MODEL))

output = model.export(
    format="onnx",
    imgsz=224,
    batch=1,
    dynamic=False,
    opset=13,
    simplify=False,
    device="cpu"
)

output = Path(output)

onnx_model = onnx.load(str(output))
onnx.checker.check_model(onnx_model)

print("\nONNX EXPORT COMPLETED")
print("-----------------------------")
print("MODEL:", output)
print("FILE SIZE:", round(output.stat().st_size / 1024**2, 2), "MB")
print("SHA256:", sha256(output))
print("ONNX STRUCTURE: VALID")
print("-----------------------------")

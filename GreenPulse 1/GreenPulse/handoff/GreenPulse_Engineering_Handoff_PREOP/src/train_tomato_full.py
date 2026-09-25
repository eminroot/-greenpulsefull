import torch
from pathlib import Path
from ultralytics import YOLO

torch.set_num_threads(12)

DATASET = Path(
    "datasets/processed/tomato_cls"
).resolve()

PROJECT = Path(
    "runs/greenpulse"
).resolve()

print("\nGREENPULSE PROFESSIONAL TRAINING")
print("--------------------------------")
print("Model: YOLO11n Classification")
print("Device: CPU")
print("Dataset:", DATASET)
print("Epochs: 15")
print("Image size: 224")
print("--------------------------------")

model = YOLO("yolo11n-cls.pt")

model.train(
    data=str(DATASET),
    epochs=15,
    imgsz=224,
    batch=32,
    device="cpu",
    workers=0,
    optimizer="AdamW",
    lr0=0.001,
    patience=5,
    seed=42,
    deterministic=True,
    auto_augment=None,
    erasing=0.0,
    fliplr=0.5,
    amp=False,
    project=str(PROJECT),
    name="tomato_cpu_v1",
    exist_ok=False,
    plots=True
)

print("\nTRAINING COMPLETED!")
print("RESULTS:", model.trainer.save_dir)

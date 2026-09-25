import torch
from pathlib import Path
from ultralytics import YOLO

# CPU optimallaşdırılması
torch.set_num_threads(12)

# Dataset
DATASET = Path("datasets/processed/tomato_smoke").resolve()

if not DATASET.exists():
    raise FileNotFoundError(DATASET)

print("\nGREENPULSE AI TRAINING")
print("----------------------------")
print("Model: YOLO11n Classification")
print("Device: CPU")
print("CPU threads:", torch.get_num_threads())
print("Dataset:", DATASET)
print("----------------------------")

# Əvvəlcədən öyrədilmiş yüngül model
model = YOLO("yolo11n-cls.pt")

# İlk texniki training
model.train(
    data=str(DATASET),
    epochs=1,
    imgsz=160,
    batch=16,
    device="cpu",
    workers=0,
    seed=42,
    deterministic=True,
    project="runs/greenpulse",
    name="tomato_cpu_smoke",
    exist_ok=True,
    plots=False
)

print("\nGREENPULSE FIRST TRAINING COMPLETED!")

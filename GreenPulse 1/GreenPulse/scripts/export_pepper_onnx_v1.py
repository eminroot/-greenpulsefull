
import hashlib
import json
import math
import os
import random
import shutil

from datetime import datetime, timezone
from pathlib import Path

# Prevent automatic package installation.
os.environ["YOLO_AUTOINSTALL"] = "False"

import onnx
import onnxruntime
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]

TRAINING = ROOT / (
    "reports/pepper_transfer_training_v1.json"
)

COMPARISON = ROOT / (
    "reports/pepper_model_comparison_v1.json"
)

SPLIT = ROOT / (
    "reports/pepper_group_split_v1.json"
)

DATASET = ROOT / (
    "datasets/processed/pepper_cls_leafgroup_v1"
)

WORK = ROOT / (
    "models/.pepper_export_work_v1"
)

RELEASE = ROOT / (
    "models/release_candidates/pepper_transfer_v1"
)

REPORT = ROOT / (
    "reports/pepper_onnx_parity_v1.json"
)

CLASSES = {
    "Pepper,_bell___Bacterial_spot":
        "bacterial_spot",
    "Pepper,_bell___healthy":
        "healthy"
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
    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


print("=" * 48)
print("GREENPULSE PEPPER ONNX EXPORT")
print("=" * 48)


# 1. PREFLIGHT

for path in (TRAINING, COMPARISON, SPLIT):
    if not path.is_file():
        raise FileNotFoundError(path)

for path in (WORK, RELEASE, REPORT):
    if path.exists():
        raise FileExistsError(
            f"Existing output: {path}"
        )

training = load_json(TRAINING)
comparison = load_json(COMPARISON)
manifest = load_json(SPLIT)

source = (
    ROOT / training["best_checkpoint"]
).resolve()

assert source.is_file()

assert (
    sha256_file(source)
    == training["best_checkpoint_sha256"]
), "Checkpoint integrity mismatch."

assert (
    comparison["split_manifest_sha256"]
    == sha256_file(SPLIT)
), "Dataset split changed."

assert (
    comparison["test_images_evaluated"]
    == 0
), "Test isolation not confirmed."

assert (
    comparison["transfer_checkpoint_sha256"]
    == training["best_checkpoint_sha256"]
)

assert (
    comparison["transfer_metrics"]["macro_f1"]
    == 1.0
)

assert (
    comparison["baseline_metrics"]["macro_f1"]
    == 1.0
)

assert not (DATASET / "test").exists()


# 2. SELECT 50 VALIDATION IMAGES

rng = random.Random(2026)

selected = []

for original_class, folder in CLASSES.items():

    candidates = sorted(
        (
            item
            for item in manifest["samples"]
            if item["split"] == "val"
            and item["class_name"] == original_class
        ),
        key=lambda item: item["path"]
    )

    assert len(candidates) >= 25

    chosen = rng.sample(candidates, 25)

    for item in chosen:
        path = (
            DATASET
            / "val"
            / folder
            / Path(item["path"]).name
        ).resolve()

        assert path.is_relative_to(
            DATASET.resolve()
        )

        assert path.is_file()

        assert (
            sha256_file(path)
            == item["sha256"]
        ), "Validation image integrity mismatch."

        selected.append({
            "path": str(path),
            "relative_path": item["path"],
            "class_name": folder,
            "sha256": item["sha256"]
        })

assert len(selected) == 50

print("Validation images selected:", len(selected))
print("Reserved test images used: 0")


# 3. EXPORT CHECKPOINT

WORK.mkdir(
    parents=True,
    exist_ok=False
)

temporary_pt = WORK / "pepper_transfer_v1.pt"

shutil.copy2(source, temporary_pt)

assert (
    sha256_file(temporary_pt)
    == training["best_checkpoint_sha256"]
)

print("\nExporting verified checkpoint...")

pt_model = YOLO(str(temporary_pt))

exported = Path(
    pt_model.export(
        format="onnx",
        imgsz=224,
        dynamic=False,
        simplify=False,
        device="cpu"
    )
).resolve()

if not exported.is_file():
    raise FileNotFoundError(
        "ONNX export file missing."
    )


# 4. VERIFY ONNX STRUCTURE

graph = onnx.load(str(exported))

onnx.checker.check_model(graph)

session = onnxruntime.InferenceSession(
    str(exported),
    providers=["CPUExecutionProvider"]
)

assert len(session.get_inputs()) == 1

print("ONNX structural verification: PASS")


# 5. PYTORCH / ONNX PARITY

onnx_model = YOLO(str(exported))

expected_names = [
    "bacterial_spot",
    "healthy"
]

for model in (pt_model, onnx_model):
    names = [
        model.names[i]
        for i in sorted(model.names)
    ]

    assert names == expected_names, (
        "Exported class mapping mismatch."
    )


def probabilities(model, image_path):
    result = model.predict(
        source=image_path,
        imgsz=224,
        device="cpu",
        batch=1,
        verbose=False,
        save=False
    )[0]

    if result.probs is None:
        raise ValueError(
            "Classification probabilities missing."
        )

    values = [
        float(value)
        for value in result.probs.data.tolist()
    ]

    if (
        len(values) != 2
        or not all(
            math.isfinite(value)
            for value in values
        )
    ):
        raise ValueError(
            "Invalid classification output."
        )

    return values


matching_predictions = 0
maximum_probability_difference = 0.0

print("\nChecking prediction parity...")

for index, item in enumerate(selected, 1):

    pt = probabilities(
        pt_model,
        item["path"]
    )

    exported_probs = probabilities(
        onnx_model,
        item["path"]
    )

    pt_class = max(
        range(2),
        key=lambda i: pt[i]
    )

    onnx_class = max(
        range(2),
        key=lambda i: exported_probs[i]
    )

    if pt_class == onnx_class:
        matching_predictions += 1

    difference = max(
        abs(a - b)
        for a, b in zip(pt, exported_probs)
    )

    maximum_probability_difference = max(
        maximum_probability_difference,
        difference
    )

    if index % 10 == 0:
        print(
            f"Compared: {index}/{len(selected)}"
        )


# 6. APPLY PARITY REQUIREMENTS

TOP1_REQUIRED = len(selected)
MAX_ALLOWED_DIFFERENCE = 0.01

if matching_predictions != TOP1_REQUIRED:
    raise ValueError(
        "PyTorch and ONNX prediction mismatch."
    )

if (
    maximum_probability_difference
    > MAX_ALLOWED_DIFFERENCE
):
    raise ValueError(
        "ONNX probability drift exceeds tolerance."
    )


# 7. PUBLISH VERIFIED CANDIDATE

RELEASE.mkdir(
    parents=True,
    exist_ok=False
)

final_pt = RELEASE / "pepper_transfer_v1.pt"
final_onnx = RELEASE / "pepper_transfer_v1.onnx"

shutil.copy2(temporary_pt, final_pt)
shutil.copy2(exported, final_onnx)

assert (
    sha256_file(final_pt)
    == training["best_checkpoint_sha256"]
)

assert (
    sha256_file(final_onnx)
    == sha256_file(exported)
)

report = {
    "version": "1.0",
    "generated_at_utc":
        datetime.now(timezone.utc).isoformat(),
    "task": "PEPPER_DISEASE_CLASSIFICATION",
    "candidate_selection_reason":
        "CONTINUITY_WITH_EXISTING_GREENPULSE_PIPELINE",
    "transfer_advantage_demonstrated": False,
    "source_checkpoint_sha256":
        training["best_checkpoint_sha256"],
    "onnx_checkpoint_sha256":
        sha256_file(final_onnx),
    "onnx_opset": [
        item.version
        for item in graph.opset_import
        if item.domain in ("", "ai.onnx")
    ],
    "onnx_structural_check_passed": True,
    "parity_samples": len(selected),
    "parity_sample_manifest": selected,
    "matching_top1_predictions":
        matching_predictions,
    "maximum_probability_difference":
        maximum_probability_difference,
    "maximum_allowed_difference":
        MAX_ALLOWED_DIFFERENCE,
    "validation_only": True,
    "test_images_evaluated": 0,
    "onnx_runtime_checked_on_cpu": True,
    "hailo_conversion_completed": False,
    "raspberry_pi_validated": False,
    "real_greenhouse_validated": False,
    "water_stress_validated": False,
    "operational_release_approved": False
}

REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        allow_nan=False
    ) + "\n",
    encoding="utf-8"
)

shutil.rmtree(WORK)


# 8. RESULTS

print("\n" + "=" * 48)
print("PEPPER ONNX EXPORT RESULTS")
print("=" * 48)

print("Structural check: PASS")

print(
    "Matching predictions:",
    matching_predictions,
    "/50"
)

print(
    "Maximum probability difference:",
    round(
        maximum_probability_difference,
        8
    )
)

print("PyTorch SHA-256:")
print(sha256_file(final_pt))

print("ONNX SHA-256:")
print(sha256_file(final_onnx))

print("\nTest dataset: UNTOUCHED")
print("Hailo conversion: PENDING")
print("Raspberry Pi validation: PENDING")
print("Operational release: NOT APPROVED")

print("\nReport:", REPORT)
print("=" * 48)
print("PEPPER ONNX PARITY: PASS")

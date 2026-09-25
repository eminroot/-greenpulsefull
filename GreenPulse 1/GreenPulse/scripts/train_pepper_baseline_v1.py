
import csv
import hashlib
import json

from datetime import datetime, timezone
from pathlib import Path

import torch
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]

CONFIG = ROOT / (
    "configs/pepper_transfer_experiment_v1.json"
)

TRANSFER_REPORT = ROOT / (
    "reports/pepper_transfer_training_v1.json"
)

VALIDATION_REPORT = ROOT / (
    "reports/pepper_validation_evaluation_v1.json"
)

SPLIT = ROOT / (
    "reports/pepper_group_split_v1.json"
)

DATASET = ROOT / (
    "datasets/processed/pepper_cls_leafgroup_v1"
)

OUTPUT = ROOT / (
    "runs/pepper_transfer/"
    "pepper_generic_baseline_v1"
)

REPORT = ROOT / (
    "reports/pepper_generic_baseline_training_v1.json"
)


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b""
        ):
            digest.update(block)

    return digest.hexdigest()


def main():

    print("=" * 48)
    print("GREENPULSE PEPPER BASELINE EXPERIMENT")
    print("=" * 48)

    # 1. Check existing experiment

    for path in (
        CONFIG,
        TRANSFER_REPORT,
        VALIDATION_REPORT,
        SPLIT
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    if OUTPUT.exists() or REPORT.exists():
        raise FileExistsError(
            "Baseline experiment already exists. "
            "Do not overwrite previous results."
        )

    config = json.loads(
        CONFIG.read_text(
            encoding="utf-8-sig"
        )
    )

    transfer = json.loads(
        TRANSFER_REPORT.read_text(
            encoding="utf-8-sig"
        )
    )

    validation = json.loads(
        VALIDATION_REPORT.read_text(
            encoding="utf-8-sig"
        )
    )

    manifest = json.loads(
        SPLIT.read_text(
            encoding="utf-8-sig"
        )
    )

    # 2. Verify completed transfer experiment

    transfer_checkpoint = (
        ROOT / transfer["best_checkpoint"]
    ).resolve()

    assert transfer_checkpoint.is_file()

    assert (
        sha256_file(transfer_checkpoint)
        == transfer["best_checkpoint_sha256"]
    )

    assert (
        validation["checkpoint_sha256"]
        == transfer["best_checkpoint_sha256"]
    )

    assert (
        validation["evaluation_split"]
        == "VALIDATION_ONLY"
    )

    assert (
        validation["test_images_evaluated"]
        == 0
    )

    assert (
        validation["split_manifest_sha256"]
        == sha256_file(SPLIT)
    )

    assert (
        config["split_manifest_sha256"]
        == sha256_file(SPLIT)
    )

    assert manifest["eligible_images"] == 2473

    assert not (
        DATASET / "test"
    ).exists()

    # 3. Verify the dataset

    expected = {
        ("train", "bacterial_spot"): 699,
        ("train", "healthy"): 1032,
        ("val", "bacterial_spot"): 149,
        ("val", "healthy"): 222
    }

    for (split, class_name), count in (
        expected.items()
    ):
        folder = (
            DATASET / split / class_name
        )

        images = [
            path for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower()
            in {".jpg", ".jpeg", ".png"}
        ]

        if len(images) != count:
            raise ValueError(
                f"Dataset count changed: {folder}"
            )

    # 4. Load the standard pretrained model

    print("\nLoading standard YOLO11n-cls...")

    print(
        "If the checkpoint is not cached, "
        "Ultralytics may download it."
    )

    model = YOLO("yolo11n-cls.pt")

    if model.task != "classify":
        raise ValueError(
            "Incorrect baseline model task."
        )

    if len(model.names) != 1000:
        raise ValueError(
            "Expected standard ImageNet "
            "classification checkpoint."
        )

    checkpoint_path = Path(
        model.ckpt_path
    ).resolve()

    if not checkpoint_path.is_file():
        raise FileNotFoundError(
            "Baseline checkpoint unavailable."
        )

    baseline_source_hash = sha256_file(
        checkpoint_path
    )

    print(
        "Baseline checkpoint:",
        checkpoint_path
    )

    print(
        "Baseline SHA-256:",
        baseline_source_hash
    )

    # 5. Use the same training configuration

    settings = config["training"]

    device = settings["device"]

    if (
        device != "cpu"
        and not torch.cuda.is_available()
    ):
        raise RuntimeError(
            "Previously selected CUDA device "
            "is no longer available."
        )

    print("\nTRAINING CONFIGURATION")
    print("Epoch budget:", settings["epochs"])
    print("Image size:", settings["imgsz"])
    print("Batch:", settings["batch"])
    print("Device:", device)
    print("Seed:", settings["seed"])

    print("\nSTARTING BASELINE TRAINING\n")

    model.train(
        data=str(DATASET),
        epochs=settings["epochs"],
        imgsz=settings["imgsz"],
        batch=settings["batch"],
        device=device,
        workers=settings["workers"],
        seed=settings["seed"],
        deterministic=settings["deterministic"],
        optimizer=settings["optimizer"],
        lr0=settings["initial_learning_rate"],
        patience=settings["patience"],
        cache=settings["cache"],
        project=str(OUTPUT.parent),
        name=OUTPUT.name,
        exist_ok=False,
        save=True,
        val=True,
        plots=True
    )

    # 6. Verify experiment output

    best = OUTPUT / "weights/best.pt"

    if not best.is_file():
        raise FileNotFoundError(
            "Baseline best.pt was not created."
        )

    trained = YOLO(str(best))

    class_names = [
        trained.names[i]
        for i in sorted(trained.names)
    ]

    if class_names != [
        "bacterial_spot",
        "healthy"
    ]:
        raise ValueError(
            "Incorrect baseline class mapping."
        )

    results_csv = OUTPUT / "results.csv"

    epochs = None

    if results_csv.is_file():

        with results_csv.open(
            newline="",
            encoding="utf-8-sig"
        ) as stream:

            epochs = sum(
                1
                for _ in csv.DictReader(stream)
            )

    # 7. Preserve experiment provenance

    report = {
        "version": "1.0",
        "generated_at_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "experiment":
            "pepper_generic_baseline_v1",

        "task":
            "PEPPER_DISEASE_CLASSIFICATION",

        "initial_checkpoint":
            str(checkpoint_path),

        "initial_checkpoint_sha256":
            baseline_source_hash,

        "best_checkpoint":
            str(best.relative_to(ROOT)),

        "best_checkpoint_sha256":
            sha256_file(best),

        "split_manifest_sha256":
            sha256_file(SPLIT),

        "training_configuration":
            settings,

        "completed_epochs":
            epochs,

        "training_completed":
            True,

        "target_classes":
            class_names,

        "validation_evaluation_completed":
            False,

        "test_evaluation_completed":
            False,

        "transfer_advantage_demonstrated":
            False,

        "real_greenhouse_validation":
            False,

        "water_stress_model_trained":
            False
    }

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            allow_nan=False
        ) + "\n",
        encoding="utf-8"
    )

    print("\n" + "=" * 48)
    print("PEPPER BASELINE TRAINING COMPLETED")
    print("Completed epochs:", epochs)
    print("Baseline classes:", class_names)
    print("Best checkpoint:", best)
    print("Best SHA-256:")
    print(report["best_checkpoint_sha256"])
    print("Validation comparison: PENDING")
    print("Test dataset: UNTOUCHED")
    print("Transfer advantage: NOT YET VERIFIED")
    print("Report:", REPORT)
    print("=" * 48)


if __name__ == "__main__":
    main()

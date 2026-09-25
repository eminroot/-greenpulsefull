
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

DATASET_REPORT = ROOT / (
    "reports/pepper_training_dataset_v1.json"
)

SPLIT = ROOT / (
    "reports/pepper_group_split_v1.json"
)

OUTPUT = ROOT / (
    "runs/pepper_transfer/"
    "pepper_tomato_transfer_v1"
)

REPORT = ROOT / (
    "reports/pepper_transfer_training_v1.json"
)

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


def main():

    print("=" * 48)
    print("GREENPULSE PEPPER TRANSFER LEARNING")
    print("=" * 48)

    # 1. PREFLIGHT

    if OUTPUT.exists():
        raise FileExistsError(
            "Training output already exists. "
            "Do not overwrite an existing experiment."
        )

    if REPORT.exists():
        raise FileExistsError(
            "Training report already exists."
        )

    config = json.loads(
        CONFIG.read_text(encoding="utf-8-sig")
    )

    build = json.loads(
        DATASET_REPORT.read_text(
            encoding="utf-8-sig"
        )
    )

    split = json.loads(
        SPLIT.read_text(encoding="utf-8-sig")
    )

    checkpoint = (
        ROOT / config["source_checkpoint"]
    ).resolve()

    dataset = (
        ROOT / config["dataset"]
    ).resolve()

    assert checkpoint.is_file()
    assert dataset.is_dir()

    assert (
        sha256_file(checkpoint)
        == config["source_checkpoint_sha256"]
    ), "Original checkpoint changed."

    assert (
        sha256_file(SPLIT)
        == config["split_manifest_sha256"]
    ), "Dataset split changed."

    assert (
        sha256_file(DATASET_REPORT)
        == config["dataset_build_report_sha256"]
    ), "Dataset build report changed."

    assert build["test_copied"] is False
    assert not (dataset / "test").exists()

    assert config["target_classes"] == [
        "bacterial_spot",
        "healthy"
    ]

    # 2. VERIFY ALL TRAINING IMAGES

    print("\nVerifying training and validation files...")

    expected_paths = set()
    train_count = 0
    val_count = 0

    for sample in split["samples"]:

        partition = sample["split"]

        if partition == "test":
            continue

        if partition not in ("train", "val"):
            raise ValueError(
                "Unexpected dataset partition."
            )

        class_name = CLASS_MAPPING[
            sample["class_name"]
        ]

        image = (
            dataset /
            partition /
            class_name /
            Path(sample["path"]).name
        ).resolve()

        if not image.is_relative_to(dataset):
            raise ValueError(
                "Unsafe dataset path."
            )

        if not image.is_file():
            raise FileNotFoundError(image)

        if sha256_file(image) != sample["sha256"]:
            raise ValueError(
                "Image integrity mismatch."
            )

        key = str(image).casefold()

        if key in expected_paths:
            raise ValueError(
                "Duplicate destination image."
            )

        expected_paths.add(key)

        if partition == "train":
            train_count += 1
        else:
            val_count += 1

    assert train_count == 1731
    assert val_count == 371

    actual_paths = set()

    for partition in ("train", "val"):

        for class_name in (
            "bacterial_spot",
            "healthy"
        ):

            folder = (
                dataset / partition / class_name
            )

            for image in folder.iterdir():

                if not image.is_file():
                    raise ValueError(
                        "Unexpected dataset entry."
                    )

                actual_paths.add(
                    str(image.resolve()).casefold()
                )

    assert actual_paths == expected_paths

    print("Training images:", train_count)
    print("Validation images:", val_count)
    print("Reserved test images: 371")

    # 3. CHECK HARDWARE

    settings = config["training"]
    device = settings["device"]

    if device != "cpu":

        if not torch.cuda.is_available():
            raise RuntimeError(
                "Configured CUDA device unavailable. "
                "Do not silently change the experiment."
            )

    print("\nTraining device:", device)
    print("Batch size:", settings["batch"])
    print("Maximum epochs:", settings["epochs"])

    # 4. LOAD EXISTING TOMATO MODEL

    print("\nLoading verified tomato checkpoint...")

    model = YOLO(str(checkpoint))

    if model.task != "classify":
        raise ValueError(
            "Source is not a classification model."
        )

    if len(model.names) != 10:
        raise ValueError(
            "Expected ten source classes."
        )

    print("Source model: VERIFIED")
    print("Source classes:", len(model.names))

    # 5. START ACTUAL TRANSFER LEARNING

    print("\nSTARTING TRANSFER LEARNING")
    print("The test set will remain isolated.\n")

    model.train(
        data=str(dataset),
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

    # 6. VERIFY SAVED MODEL

    best = OUTPUT / "weights/best.pt"
    last = OUTPUT / "weights/last.pt"

    if not best.is_file():
        raise FileNotFoundError(
            "Training finished without best.pt."
        )

    trained_model = YOLO(str(best))

    names = trained_model.names

    actual_names = [
        names[index]
        for index in sorted(names)
    ]

    expected_names = [
        "bacterial_spot",
        "healthy"
    ]

    if actual_names != expected_names:
        raise ValueError(
            "Trained model class mapping mismatch: "
            + str(actual_names)
        )

    # 7. RECORD EXPERIMENT

    results_csv = OUTPUT / "results.csv"

    completed_epochs = None

    if results_csv.is_file():

        with results_csv.open(
            newline="",
            encoding="utf-8-sig"
        ) as stream:

            completed_epochs = sum(
                1
                for _ in csv.DictReader(stream)
            )

    report = {
        "version": "1.0",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "project": "GreenPulse",
        "task": "PEPPER_DISEASE_CLASSIFICATION",
        "experiment":
            "pepper_tomato_transfer_v1",
        "initial_checkpoint": str(
            checkpoint.relative_to(ROOT)
        ),
        "initial_checkpoint_sha256":
            config["source_checkpoint_sha256"],
        "best_checkpoint": str(
            best.relative_to(ROOT)
        ),
        "best_checkpoint_sha256":
            sha256_file(best),
        "last_checkpoint_exists":
            last.is_file(),
        "source_classes": 10,
        "target_classes": actual_names,
        "training_images": train_count,
        "validation_images": val_count,
        "reserved_test_images": 371,
        "maximum_epochs": settings["epochs"],
        "completed_epochs": completed_epochs,
        "training_completed": True,
        "test_evaluation_completed": False,
        "comparison_experiment_completed": False,
        "transfer_advantage_demonstrated": False,
        "physical_plant_identity_verified": False,
        "real_greenhouse_validation": False,
        "water_stress_model_trained": False,
        "physical_actuation_authorized": False
    }

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORT.write_text(
        json.dumps(
            report,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print("\n" + "=" * 48)
    print("PEPPER TRANSFER TRAINING COMPLETED")
    print("Source checkpoint: VERIFIED")
    print("Target classes:", actual_names)
    print("Completed epochs:", completed_epochs)
    print("Best checkpoint:", best)
    print("Best checkpoint SHA-256:")
    print(report["best_checkpoint_sha256"])
    print("Reserved test evaluation: NOT STARTED")
    print("Transfer advantage: NOT YET VERIFIED")
    print("Water stress detection: NOT TRAINED")
    print("Report:", REPORT)
    print("=" * 48)


if __name__ == "__main__":
    main()

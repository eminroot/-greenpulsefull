
import hashlib
import io
import json
import os
import shutil
import tempfile

from pathlib import Path
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from src.real_multimodal_readiness import (
    assess_real_data_candidate
)


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_STAGING = (
    ROOT / "data" / "real_candidate_staging"
)

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


def stage_multimodal_candidate(
    image_path,
    metadata,
    staging_dir=None
):
    """
    Offline, non-destructive candidate-data intake.

    Does not authenticate physical devices.
    Does not authorize model training.
    Does not perform physical actuation.
    """

    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be an object.")

    readiness = assess_real_data_candidate(
        metadata
    )

    if not readiness["schema_valid"]:
        raise ValueError(
            "Invalid metadata: "
            + ",".join(
                readiness["blocking_reasons"]
            )
        )

    if readiness["status"] == "REJECTED":
        raise ValueError(
            "Metadata rejected: "
            + ",".join(
                readiness["blocking_reasons"]
            )
        )

    sample_id = str(
        UUID(metadata["sample_id"])
    )

    source = Path(image_path).resolve()

    if not source.is_file():
        raise FileNotFoundError(
            "Source image does not exist."
        )

    if source.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError(
            "Image exceeds the 8 MB limit."
        )

    content = source.read_bytes()

    if (
        not content
        or len(content) > MAX_IMAGE_BYTES
    ):
        raise ValueError("Invalid image size.")

    digest = hashlib.sha256(
        content
    ).hexdigest()

    expected = metadata[
        "camera"
    ]["image_sha256"].lower()

    if digest != expected:
        raise ValueError(
            "IMAGE_SHA256_MISMATCH"
        )

    try:
        with Image.open(
            io.BytesIO(content)
        ) as image:
            image_format = image.format
            width, height = image.size

            if (
                width < 96
                or height < 96
                or width * height > MAX_IMAGE_PIXELS
            ):
                raise ValueError(
                    "Unsupported image dimensions."
                )

            if image_format not in (
                "JPEG",
                "PNG"
            ):
                raise ValueError(
                    "Unsupported image format."
                )

            image.verify()

        # Decode again: verify() alone does not
        # guarantee complete image decoding.
        with Image.open(
            io.BytesIO(content)
        ) as image:
            image.load()

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError
    ) as exc:
        raise ValueError(
            "IMAGE_DECODE_FAILED"
        ) from exc

    extension = (
        ".jpg"
        if image_format == "JPEG"
        else ".png"
    )

    destination_root = (
        Path(staging_dir).resolve()
        if staging_dir is not None
        else DEFAULT_STAGING.resolve()
    )

    final_dir = (
        destination_root / sample_id
    )

    if final_dir.exists():
        raise FileExistsError(
            "Sample ID already staged."
        )

    report = {
        "intake_version": "0.1.0",
        "sample_id": sample_id,
        "image_sha256": digest,
        "image_format": image_format,
        "image_width": width,
        "image_height": height,
        "storage_status": "STAGED",
        "readiness": readiness,
        "device_authenticated": False,
        "training_eligible": False,
        "physical_actuation_allowed": False
    }

    # Validate serializability before writing.
    metadata_bytes = (
        json.dumps(
            metadata,
            indent=2,
            allow_nan=False
        ) + "\n"
    ).encode("utf-8")

    report_bytes = (
        json.dumps(
            report,
            indent=2,
            allow_nan=False
        ) + "\n"
    ).encode("utf-8")

    destination_root.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_dir = Path(
        tempfile.mkdtemp(
            prefix=".staging-",
            dir=destination_root
        )
    )

    try:
        (
            temporary_dir /
            ("frame" + extension)
        ).write_bytes(content)

        (
            temporary_dir /
            "metadata.json"
        ).write_bytes(metadata_bytes)

        (
            temporary_dir /
            "intake_report.json"
        ).write_bytes(report_bytes)

        # Publish the complete sample only
        # after all files have been written.
        if final_dir.exists():
            raise FileExistsError(
                "Duplicate sample detected."
            )

        os.rename(
            temporary_dir,
            final_dir
        )

    finally:
        if temporary_dir.exists():
            shutil.rmtree(
                temporary_dir
            )

    return {
        **report,
        "staging_path": str(final_dir)
    }

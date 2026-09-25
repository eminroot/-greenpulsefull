
import hashlib
import json

from collections import defaultdict
from pathlib import Path
from uuid import UUID

from src.real_multimodal_readiness import (
    assess_real_data_candidate
)


MAX_METADATA_BYTES = 65536
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def read_json_safely(path):
    if (
        not path.is_file()
        or path.stat().st_size > MAX_METADATA_BYTES
    ):
        raise ValueError("Missing or oversized JSON file.")

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def audit_staged_candidates(staging_root):
    """
    Read-only integrity audit.

    Does not authenticate devices.
    Does not approve model training.
    Does not communicate with physical hardware.
    """

    root = Path(staging_root).resolve()

    if not root.is_dir():
        raise FileNotFoundError(
            "Staging directory does not exist."
        )

    records = []
    digest_index = defaultdict(list)

    folders = sorted(
        p for p in root.iterdir()
        if p.is_dir()
    )

    for folder in folders:
        record = {
            "sample_id": folder.name,
            "image_sha256": None,
            "file_integrity_pass": False,
            "image_sensor_aligned": False,
            "device_authenticated": False,
            "training_eligible": False,
            "physical_actuation_allowed": False,
            "status": "REVIEW_REQUIRED",
            "issues": []
        }

        issues = record["issues"]

        try:
            sample_id = str(UUID(folder.name))

            if sample_id != folder.name:
                issues.append(
                    "NON_CANONICAL_SAMPLE_DIRECTORY"
                )

        except (ValueError, TypeError):
            issues.append(
                "INVALID_SAMPLE_DIRECTORY"
            )

        try:
            metadata = read_json_safely(
                folder / "metadata.json"
            )

            report = read_json_safely(
                folder / "intake_report.json"
            )

        except (ValueError, OSError, json.JSONDecodeError):
            issues.append(
                "METADATA_OR_REPORT_UNAVAILABLE"
            )

            records.append(record)
            continue

        readiness = assess_real_data_candidate(
            metadata
        )

        if not readiness["schema_valid"]:
            issues.append(
                "INVALID_STORED_METADATA"
            )

        record["image_sensor_aligned"] = (
            readiness["image_sensor_aligned"]
        )

        if not record["image_sensor_aligned"]:
            issues.append(
                "IMAGE_SENSOR_TIME_MISMATCH"
            )

        if metadata.get("sample_id") != folder.name:
            issues.append(
                "METADATA_SAMPLE_ID_MISMATCH"
            )

        if report.get("sample_id") != folder.name:
            issues.append(
                "REPORT_SAMPLE_ID_MISMATCH"
            )

        if report.get("storage_status") != "STAGED":
            issues.append(
                "INVALID_INTAKE_STATUS"
            )

        if (
            report.get("training_eligible") is not False
            or report.get(
                "physical_actuation_allowed"
            ) is not False
        ):
            issues.append(
                "UNSAFE_INTAKE_REPORT"
            )

        if report.get("readiness") != readiness:
            issues.append(
                "READINESS_REPORT_MISMATCH"
            )

        images = [
            p for p in folder.iterdir()
            if p.is_file()
            and p.name in ("frame.jpg", "frame.png")
        ]

        if len(images) != 1:
            issues.append(
                "MISSING_OR_AMBIGUOUS_IMAGE"
            )

            records.append(record)
            continue

        image = images[0]

        if image.stat().st_size > MAX_IMAGE_BYTES:
            issues.append(
                "IMAGE_EXCEEDS_SIZE_LIMIT"
            )

            records.append(record)
            continue

        digest = hashlib.sha256()

        with image.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)

                if not chunk:
                    break

                digest.update(chunk)

        actual_hash = digest.hexdigest()

        record["image_sha256"] = actual_hash

        expected_hash = (
            metadata.get("camera", {})
            .get("image_sha256", "")
        )

        if actual_hash != str(expected_hash).lower():
            issues.append(
                "IMAGE_METADATA_HASH_MISMATCH"
            )

        if actual_hash != report.get("image_sha256"):
            issues.append(
                "IMAGE_REPORT_HASH_MISMATCH"
            )

        # Duplicate detection applies only to
        # samples with otherwise consistent
        # metadata and image integrity.
        integrity_issues = [
            issue for issue in issues
            if issue != "IMAGE_SENSOR_TIME_MISMATCH"
        ]

        if not integrity_issues:
            digest_index[actual_hash].append(record)

        records.append(record)

    for digest, matching in digest_index.items():
        if len(matching) > 1:
            for record in matching:
                record["issues"].append(
                    "DUPLICATE_IMAGE_CONTENT"
                )

    for record in records:
        record["file_integrity_pass"] = (
            len(record["issues"]) == 0
        )

        record["status"] = (
            "STAGED_UNVERIFIED"
            if record["file_integrity_pass"]
            else "REVIEW_REQUIRED"
        )

    return {
        "audit_version": "0.1.0",
        "total_candidates": len(records),
        "integrity_pass_count": sum(
            r["file_integrity_pass"]
            for r in records
        ),
        "review_required_count": sum(
            not r["file_integrity_pass"]
            for r in records
        ),
        "device_authentication_performed": False,
        "training_approved": False,
        "physical_actuation_allowed": False,
        "samples": records
    }


import json
import os
import tempfile

from pathlib import Path

from src.staging_integrity_audit import (
    audit_staged_candidates
)


MANIFEST_VERSION = "0.1.0"


def generate_candidate_manifest(
    staging_root,
    output_path
):
    """
    Generate a candidate dataset inventory.

    Read-only with respect to staged samples.

    No automatic training approval.
    No train/validation/test split is generated.
    """

    root = Path(staging_root).resolve()
    output = Path(output_path).resolve()

    if not root.is_dir():
        raise FileNotFoundError(
            "Candidate staging folder not found."
        )

    # Never place generated reports among
    # the directories being audited.
    if output.is_relative_to(root):
        raise ValueError(
            "Manifest must be outside staging directory."
        )

    audit = audit_staged_candidates(root)

    entries = []

    for record in audit["samples"]:
        sample_id = record["sample_id"]

        entry = {
            "sample_id": sample_id,
            "plant_id_claim": None,
            "session_id_claim": None,
            "crop": None,
            "image_sha256": record["image_sha256"],
            "plant_group_claim": None,
            "image_sensor_aligned": record[
                "image_sensor_aligned"
            ],
            "integrity_pass": record[
                "file_integrity_pass"
            ],
            "status": record["status"],
            "issues": list(record["issues"]),
            "device_authenticated": False,
            "ground_truth_verified": False,
            "training_eligible": False,
            "operational_actuation_allowed": False
        }

        # Read grouping metadata only when
        # the staged record passed integrity checks.
        if record["file_integrity_pass"]:
            metadata_path = (
                root / sample_id / "metadata.json"
            )

            metadata = json.loads(
                metadata_path.read_text(
                    encoding="utf-8-sig"
                )
            )

            entry["plant_id_claim"] = metadata[
                "plant_id"
            ]

            entry["session_id_claim"] = metadata[
                "session_id"
            ]

            entry["crop"] = metadata["crop"]

            # Claimed group identity only.
            # It does not verify physical plant identity.
            entry["plant_group_claim"] = metadata[
                "plant_id"
            ]

        entries.append(entry)

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "data_class": "UNVERIFIED_CANDIDATES",
        "total_samples": len(entries),
        "integrity_pass_count": sum(
            entry["integrity_pass"]
            for entry in entries
        ),
        "review_required_count": sum(
            entry["status"] == "REVIEW_REQUIRED"
            for entry in entries
        ),
        "verified_physical_plant_groups": False,
        "device_authentication_performed": False,
        "ground_truth_verified": False,
        "training_approved": False,
        "operational_actuation_allowed": False,
        "train_validation_test_split_created": False,
        "samples": sorted(
            entries,
            key=lambda item: item["sample_id"]
        )
    }

    # Write the report atomically.
    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=".manifest-",
            dir=output.parent,
            delete=False
        ) as stream:

            temporary_path = Path(
                stream.name
            )

            json.dump(
                manifest,
                stream,
                indent=2,
                allow_nan=False
            )

            stream.write("\n")

        os.replace(
            temporary_path,
            output
        )

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()

    return manifest

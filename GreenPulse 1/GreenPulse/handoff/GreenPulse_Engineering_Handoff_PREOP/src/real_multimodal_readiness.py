
import json
import math

from datetime import datetime
from pathlib import Path

from jsonschema import (
    Draft202012Validator,
    FormatChecker
)


ROOT = Path(__file__).resolve().parents[1]

SCHEMA = json.loads(
    (
        ROOT
        / "configs"
        / "real_multimodal_sample_schema_v1.json"
    ).read_text(encoding="utf-8")
)

VALIDATOR = Draft202012Validator(
    SCHEMA,
    format_checker=FormatChecker()
)

# Provisional data-pairing tolerance.
# This is NOT a validated operational threshold.
PAIRING_TOLERANCE_SECONDS = 120


def assess_real_data_candidate(record):
    """
    Offline metadata-quality assessment.

    A valid JSON record does NOT prove that
    the measurements came from real hardware.

    No record is authorized for model training
    or physical actuation at this stage.
    """

    result = {
        "contract_version": "0.1.0",
        "status": "REJECTED",
        "schema_valid": False,
        "image_sensor_aligned": False,
        "device_authenticated": False,
        "ground_truth_verified": False,
        "training_eligible": False,
        "operational_actuation_allowed": False,
        "blocking_reasons": []
    }

    errors = list(
        VALIDATOR.iter_errors(record)
    )

    if errors:
        result["blocking_reasons"] = sorted(
            {
                "INVALID_METADATA:"
                + ".".join(
                    map(str, error.path)
                )
                for error in errors
            }
        )

        return result

    result["schema_valid"] = True

    values = (
        record["sensor"]["soil_moisture_pct"],
        record["sensor"]["air_temperature_c"],
        record["sensor"]["relative_humidity_pct"]
    )

    if not all(
        math.isfinite(value)
        for value in values
    ):
        result["blocking_reasons"] = [
            "NON_FINITE_SENSOR_VALUE"
        ]

        return result

    image_time = datetime.fromisoformat(
        record["camera"]["captured_at"].replace(
            "Z", "+00:00"
        )
    )

    sensor_time = datetime.fromisoformat(
        record["sensor"]["observed_at"].replace(
            "Z", "+00:00"
        )
    )

    if (
        image_time.tzinfo is None
        or sensor_time.tzinfo is None
    ):
        result["blocking_reasons"] = [
            "TIMEZONE_REQUIRED"
        ]

        return result

    difference = abs(
        (
            image_time - sensor_time
        ).total_seconds()
    )

    result["image_sensor_aligned"] = (
        difference <= PAIRING_TOLERANCE_SECONDS
    )

    reasons = [
        "DEVICE_PROVENANCE_NOT_AUTHENTICATED",
        "GROUND_TRUTH_NOT_VERIFIED"
    ]

    if not result["image_sensor_aligned"]:
        reasons.append(
            "IMAGE_SENSOR_TIME_MISMATCH"
        )

    if (
        record["sensor"]["calibration_record_id"]
        is None
    ):
        reasons.append(
            "SENSOR_CALIBRATION_MISSING"
        )
    else:
        reasons.append(
            "SENSOR_CALIBRATION_NOT_INDEPENDENTLY_VERIFIED"
        )

    result["status"] = "STAGED_NOT_TRAINING_READY"

    result["blocking_reasons"] = reasons

    return result

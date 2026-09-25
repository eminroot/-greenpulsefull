from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import math


SCHEMA_VERSION = "greenpulse.stress_risk_score.v1"

EXPECTED_CALIBRATION_SCHEMA_VERSION = (
    "greenpulse.risk_calibration.v1"
)

ALLOWED_PROBABILITY_SOURCE = (
    "CALIBRATED_MULTIMODAL_FUSION"
)


def _finite_float(
    value: Any,
    name: str,
) -> float:

    if isinstance(value, bool):
        raise ValueError(
            f"{name} must be numeric."
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"{name} must be finite."
        )

    return result


def _validate_probability(
    value: Any,
) -> float:

    probability = _finite_float(
        value,
        "calibrated_probability",
    )

    if not 0.0 <= probability <= 1.0:
        raise ValueError(
            "calibrated_probability must be in [0, 1]."
        )

    return probability


def _normalize_timestamp(
    value: str,
) -> str:

    if not isinstance(value, str):
        raise ValueError(
            "timestamp must be an ISO-8601 string."
        )

    try:

        dt = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:

        raise ValueError(
            "Invalid timestamp."
        ) from exc

    if dt.tzinfo is None:
        raise ValueError(
            "Timestamp timezone is required."
        )

    return dt.astimezone(
        timezone.utc
    ).isoformat()


def _validate_calibration_artifact(
    artifact: Mapping[str, Any],
    *,
    model_version: str,
    feature_vector_version: str,
) -> dict[str, str]:

    if not isinstance(
        artifact,
        Mapping,
    ):
        raise ValueError(
            "Calibration artifact must be a mapping."
        )

    if (
        artifact.get(
            "schema_version"
        )
        != EXPECTED_CALIBRATION_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported calibration schema."
        )

    if (
        artifact.get(
            "status"
        )
        != "VALIDATED"
    ):
        raise ValueError(
            "Calibration artifact is not VALIDATED."
        )

    calibration_version = artifact.get(
        "version"
    )

    if not isinstance(
        calibration_version,
        str,
    ) or not calibration_version.strip():

        raise ValueError(
            "Calibration version is required."
        )

    artifact_model_version = artifact.get(
        "model_version"
    )

    if artifact_model_version != model_version:
        raise ValueError(
            "CALIBRATION_MODEL_VERSION_MISMATCH"
        )

    artifact_feature_version = artifact.get(
        "feature_vector_version"
    )

    if (
        artifact_feature_version
        != feature_vector_version
    ):
        raise ValueError(
            "CALIBRATION_FEATURE_VERSION_MISMATCH"
        )

    return {
        "calibration_version":
            calibration_version,

        "model_version":
            artifact_model_version,

        "feature_vector_version":
            artifact_feature_version,
    }


def blocked_stress_risk_score(
    *,
    reason: str,
    model_version: str,
    feature_vector_version: str,
    timestamp: str,
) -> dict[str, Any]:

    normalized_timestamp = (
        _normalize_timestamp(
            timestamp
        )
    )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "status":
            "BLOCKED",

        "blocking_reason":
            str(reason),

        "stress_risk_score":
            None,

        "calibrated_probability":
            None,

        "score_range": {
            "minimum":
                0.0,

            "maximum":
                100.0,
        },

        "risk_band":
            None,

        "model_version":
            model_version,

        "feature_vector_version":
            feature_vector_version,

        "calibration_version":
            None,

        "timestamp":
            normalized_timestamp,

        "scientific_guardrails": {
            "raw_yolo_confidence_used":
                False,

            "raw_disease_confidence_used":
                False,

            "uncalibrated_fusion_probability_used":
                False,

            "threshold_band_assigned":
                False,

            "physical_action_authorized":
                False,
        },
    }


def build_stress_risk_score(
    *,
    calibrated_probability: Any,
    probability_source: str,
    calibration_artifact: Optional[
        Mapping[str, Any]
    ],
    model_version: str,
    feature_vector_version: str,
    timestamp: str,
) -> dict[str, Any]:

    normalized_timestamp = (
        _normalize_timestamp(
            timestamp
        )
    )

    if (
        probability_source
        != ALLOWED_PROBABILITY_SOURCE
    ):

        raise ValueError(
            "Risk score requires calibrated "
            "multimodal fusion probability."
        )

    if calibration_artifact is None:

        return blocked_stress_risk_score(
            reason=(
                "VALIDATED_CALIBRATION_ARTIFACT_REQUIRED"
            ),
            model_version=
                model_version,
            feature_vector_version=
                feature_vector_version,
            timestamp=
                normalized_timestamp,
        )

    calibration = (
        _validate_calibration_artifact(
            calibration_artifact,
            model_version=
                model_version,
            feature_vector_version=
                feature_vector_version,
        )
    )

    probability = _validate_probability(
        calibrated_probability
    )

    score = round(
        probability * 100.0,
        6,
    )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "status":
            "SCORE_AVAILABLE",

        "blocking_reason":
            None,

        "stress_risk_score":
            score,

        "calibrated_probability":
            probability,

        "probability_source":
            probability_source,

        "score_range": {
            "minimum":
                0.0,

            "maximum":
                100.0,
        },

        # Layer 27 owns threshold optimization.
        "risk_band":
            None,

        "model_version":
            model_version,

        "feature_vector_version":
            feature_vector_version,

        "calibration_version":
            calibration[
                "calibration_version"
            ],

        "timestamp":
            normalized_timestamp,

        "scientific_guardrails": {
            "raw_yolo_confidence_used":
                False,

            "raw_disease_confidence_used":
                False,

            "uncalibrated_fusion_probability_used":
                False,

            "threshold_band_assigned":
                False,

            "thresholds_owned_by_layer_27":
                True,

            "score_authorizes_physical_action":
                False,

            "physical_action_authorized":
                False,
        },
    }
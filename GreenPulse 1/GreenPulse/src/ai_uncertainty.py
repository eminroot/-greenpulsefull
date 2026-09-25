from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import math


SCHEMA_VERSION = (
    "greenpulse.ai_uncertainty_ood.v1"
)


VALID_STATES = {
    "CONFIDENT",
    "UNCERTAIN",
    "RECHECK_REQUIRED",
}


VALID_SENSOR_STATUSES = {
    "MISSING",
    "INVALID",
    "STALE",
    "VALID_SIMULATED",
    "VALID",
}


def _finite_probability(
    value: Any,
    name: str,
) -> float:

    if isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{name} must be numeric."
        )

    result = float(
        value
    )

    if not math.isfinite(
        result
    ):
        raise ValueError(
            f"{name} must be finite."
        )

    if not (
        0.0
        <= result
        <= 1.0
    ):
        raise ValueError(
            f"{name} must be in [0, 1]."
        )

    return result


def _strict_bool(
    value: Any,
    name: str,
) -> bool:

    if type(value) is not bool:

        raise ValueError(
            f"{name} must be boolean."
        )

    return value


def _normalize_sensor_validation(
    sensor_validation: Any,
) -> tuple[str, str]:

    if sensor_validation is None:

        return (
            "MISSING",
            "sensor_validation_missing",
        )


    if isinstance(
        sensor_validation,
        Mapping,
    ):

        status = sensor_validation.get(
            "status"
        )

        reason = sensor_validation.get(
            "reason"
        )


    elif (
        isinstance(
            sensor_validation,
            (tuple, list),
        )
        and len(
            sensor_validation
        ) == 2
    ):

        status = sensor_validation[0]
        reason = sensor_validation[1]


    else:

        raise ValueError(
            "sensor_validation must be "
            "(status, reason) or mapping."
        )


    if status not in VALID_SENSOR_STATUSES:

        raise ValueError(
            "Unsupported sensor validation status."
        )


    if reason is None:

        reason = ""


    return (
        str(
            status
        ),
        str(
            reason
        ),
    )


def _normalize_image_quality(
    image_quality: Optional[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    if image_quality is None:

        return {
            "status":
                "MISSING",

            "eligible_for_inference":
                False,

            "reason":
                "IMAGE_QUALITY_RESULT_MISSING",

            "blur_threshold_validated":
                False,
        }


    if not isinstance(
        image_quality,
        Mapping,
    ):

        raise ValueError(
            "image_quality must be a mapping."
        )


    status = image_quality.get(
        "status"
    )


    eligible = image_quality.get(
        "eligible_for_inference"
    )


    if type(
        eligible
    ) is not bool:

        raise ValueError(
            "image_quality.eligible_for_inference "
            "must be boolean."
        )


    blur_validated = image_quality.get(
        "blur_threshold_validated",
        False,
    )


    if type(
        blur_validated
    ) is not bool:

        raise ValueError(
            "blur_threshold_validated must be boolean."
        )


    return {
        "status":
            status,

        "eligible_for_inference":
            eligible,

        "reason":
            image_quality.get(
                "reason"
            ),

        "blur_threshold_validated":
            blur_validated,

        "blur_score":
            image_quality.get(
                "blur_score"
            ),
    }


def evaluate_uncertainty(
    *,
    model_confidence: Optional[Any],
    model_confidence_source: Optional[str],
    low_confidence_threshold: Optional[Any],
    confidence_threshold_validated: bool,
    image_quality: Optional[
        Mapping[str, Any]
    ],
    sensor_validation: Any,
    inference_error: bool = False,
    ood_suspected: bool = False,
    unusual_feature_combination: bool = False,
) -> dict[str, Any]:

    inference_error = _strict_bool(
        inference_error,
        "inference_error",
    )

    ood_suspected = _strict_bool(
        ood_suspected,
        "ood_suspected",
    )

    unusual_feature_combination = (
        _strict_bool(
            unusual_feature_combination,
            "unusual_feature_combination",
        )
    )

    confidence_threshold_validated = (
        _strict_bool(
            confidence_threshold_validated,
            "confidence_threshold_validated",
        )
    )


    image = _normalize_image_quality(
        image_quality
    )


    (
        sensor_status,
        sensor_reason,
    ) = _normalize_sensor_validation(
        sensor_validation
    )


    uncertain_reasons = []

    recheck_reasons = []


    confidence = None

    threshold = None


    if model_confidence is None:

        recheck_reasons.append(
            "MODEL_CONFIDENCE_MISSING"
        )

    else:

        confidence = _finite_probability(
            model_confidence,
            "model_confidence",
        )


        if (
            not isinstance(
                model_confidence_source,
                str,
            )
            or not model_confidence_source.strip()
        ):

            raise ValueError(
                "model_confidence_source is required "
                "when confidence is supplied."
            )


        if low_confidence_threshold is None:

            uncertain_reasons.append(
                "CONFIDENCE_THRESHOLD_UNAVAILABLE"
            )

        else:

            threshold = _finite_probability(
                low_confidence_threshold,
                "low_confidence_threshold",
            )


            if not confidence_threshold_validated:

                uncertain_reasons.append(
                    "CONFIDENCE_THRESHOLD_NOT_VALIDATED"
                )


            if confidence <= threshold:

                uncertain_reasons.append(
                    "LOW_CONFIDENCE"
                )


    if (
        image[
            "status"
        ] != "IMAGE_OK"
        or image[
            "eligible_for_inference"
        ] is not True
    ):

        recheck_reasons.append(
            "IMAGE_QUALITY_FAILURE"
        )


    if sensor_status == "MISSING":

        recheck_reasons.append(
            "SENSOR_MISSING"
        )

    elif sensor_status == "INVALID":

        recheck_reasons.append(
            "SENSOR_INVALID"
        )

    elif sensor_status == "STALE":

        recheck_reasons.append(
            "SENSOR_STALE"
        )

    elif sensor_status == "VALID_SIMULATED":

        recheck_reasons.append(
            "SENSOR_SIMULATED"
        )


    if inference_error:

        recheck_reasons.append(
            "MODEL_FAILURE"
        )


    if ood_suspected:

        recheck_reasons.append(
            "OOD_SUSPECTED"
        )


    if unusual_feature_combination:

        recheck_reasons.append(
            "UNUSUAL_FEATURE_COMBINATION"
        )


    if recheck_reasons:

        state = "RECHECK_REQUIRED"

    elif uncertain_reasons:

        state = "UNCERTAIN"

    else:

        state = "CONFIDENT"


    if state not in VALID_STATES:

        raise RuntimeError(
            "Invalid uncertainty state."
        )


    reason_codes = list(
        dict.fromkeys(
            recheck_reasons
            + uncertain_reasons
        )
    )


    review_required = (
        state
        != "CONFIDENT"
    )


    uncertainty_action = (
        "PASS_TO_SAFETY_POLICY"
        if state
        == "CONFIDENT"
        else
        "BLOCK_AUTOMATIC_ACTION_AND_RECHECK"
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "state":
            state,

        "reason_codes":
            reason_codes,

        "review_required":
            review_required,

        "human_review_required":
            review_required,

        "uncertainty_action":
            uncertainty_action,

        "confidence": {
            "value":
                confidence,

            "source":
                (
                    model_confidence_source
                    if confidence
                    is not None
                    else None
                ),

            "low_confidence_threshold":
                threshold,

            "threshold_validated":
                confidence_threshold_validated,
        },

        "image_quality": {
            "status":
                image[
                    "status"
                ],

            "eligible_for_inference":
                image[
                    "eligible_for_inference"
                ],

            "blur_threshold_validated":
                image[
                    "blur_threshold_validated"
                ],

            "blur_used_as_hard_gate":
                False,
        },

        "sensor_validation": {
            "status":
                sensor_status,

            "reason":
                sensor_reason,
        },

        "ood": {
            "ood_suspected":
                ood_suspected,

            "unusual_feature_combination":
                unusual_feature_combination,

            "trained_ood_model_used":
                False,

            "real_ood_validation_available":
                False,
        },

        "scientific_guardrails": {
            "confidence_used_as_water_stress_probability":
                False,

            "disease_confidence_reinterpreted_as_water_stress":
                False,

            "unvalidated_blur_threshold_used":
                False,

            "trained_ood_detector_claimed":
                False,

            "real_ood_performance_claimed":
                False,

            "uncertain_observation_allows_automatic_action":
                False,

            "layer30_authorizes_physical_action":
                False,

            "physical_action_authorized":
                False,
        },
    }
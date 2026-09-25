from __future__ import annotations

from typing import Any, Mapping, Optional

import math
import numpy as np

from src.feature_fusion import (
    FUSION_FEATURE_NAMES,
)

from src.multimodal_fusion_model import (
    MultimodalFusionModel,
    extract_fusion_vector,
)


SCHEMA_VERSION = (
    "greenpulse.decision_explainability.v1"
)


STANDARD_REASON_CODES = (
    "VISUAL_STRESS_HIGH",
    "VISUAL_DELTA_HIGH",
    "LOW_SOIL_MOISTURE",
    "HIGH_TEMPERATURE",
    "RISK_TREND_RISING",
    "FORECAST_RISK_RISING",
    "TEMPORAL_CONFIRMATION",
    "LOW_CONFIDENCE",
    "IMAGE_QUALITY_LOW",
    "SENSOR_DATA_INVALID",
    "VISION_SENSOR_CONFLICT",
)


REASON_TEXT = {
    "VISUAL_STRESS_HIGH":
        (
            "The structured visual signal indicates "
            "high plant stress."
        ),

    "VISUAL_DELTA_HIGH":
        (
            "The structured visual-delta signal indicates "
            "a notable change from the plant baseline."
        ),

    "LOW_SOIL_MOISTURE":
        (
            "The structured sensor signal indicates "
            "low soil moisture."
        ),

    "HIGH_TEMPERATURE":
        (
            "The structured sensor signal indicates "
            "high temperature."
        ),

    "RISK_TREND_RISING":
        (
            "The temporal risk trend is rising."
        ),

    "FORECAST_RISK_RISING":
        (
            "The structured forecast signal indicates "
            "rising near-term risk."
        ),

    "TEMPORAL_CONFIRMATION":
        (
            "The stress condition has temporal confirmation."
        ),

    "LOW_CONFIDENCE":
        (
            "Low model confidence triggered additional caution."
        ),

    "IMAGE_QUALITY_LOW":
        (
            "Image quality did not satisfy the required "
            "quality state."
        ),

    "SENSOR_DATA_INVALID":
        (
            "Sensor data is missing, stale, invalid, "
            "or otherwise unsuitable for the operational path."
        ),

    "VISION_SENSOR_CONFLICT":
        (
            "Vision and sensor signals are in conflict."
        ),
}


def _strict_bool(
    value: Any,
    name: str,
) -> bool:

    if type(value) is not bool:

        raise ValueError(
            f"{name} must be boolean."
        )

    return value


def _normalize_reason_flags(
    reason_flags: Mapping[
        str,
        Any,
    ],
) -> dict[str, bool]:

    if not isinstance(
        reason_flags,
        Mapping,
    ):

        raise ValueError(
            "reason_flags must be a mapping."
        )


    unknown = (
        set(
            reason_flags
        )
        - set(
            STANDARD_REASON_CODES
        )
    )


    if unknown:

        raise ValueError(
            "Unsupported standard reason code(s): "
            + ", ".join(
                sorted(
                    unknown
                )
            )
        )


    normalized = {}


    for code in STANDARD_REASON_CODES:

        normalized[
            code
        ] = _strict_bool(
            reason_flags.get(
                code,
                False,
            ),
            code,
        )


    return normalized


def _normalize_decision(
    decision_result: Mapping[
        str,
        Any,
    ],
) -> tuple[
    str,
    list[str],
]:

    if not isinstance(
        decision_result,
        Mapping,
    ):

        raise ValueError(
            "decision_result must be a mapping."
        )


    decision = decision_result.get(
        "decision"
    )


    if (
        not isinstance(
            decision,
            str,
        )
        or not decision.strip()
    ):

        raise ValueError(
            "decision_result.decision is required."
        )


    raw_reasons = decision_result.get(
        "reason_codes",
        [],
    )


    if not isinstance(
        raw_reasons,
        list,
    ):

        raise ValueError(
            "decision_result.reason_codes must be a list."
        )


    if not all(
        isinstance(
            item,
            str,
        )
        for item in raw_reasons
    ):

        raise ValueError(
            "Decision reason codes must be strings."
        )


    return (
        decision.strip(),
        list(
            raw_reasons
        ),
    )


def _sigmoid_scalar(
    value: float,
) -> float:

    value = float(
        np.clip(
            value,
            -35.0,
            35.0,
        )
    )

    return (
        1.0
        / (
            1.0
            + math.exp(
                -value
            )
        )
    )


def calculate_fusion_contributions(
    *,
    fusion_model: MultimodalFusionModel,
    fused_features: Mapping[
        str,
        Any,
    ],
    top_k: int = 8,
) -> dict[str, Any]:

    if not isinstance(
        fusion_model,
        MultimodalFusionModel,
    ):

        raise ValueError(
            "fusion_model must be a MultimodalFusionModel."
        )


    if (
        fusion_model.feature_names
        != list(
            FUSION_FEATURE_NAMES
        )
    ):

        raise ValueError(
            "Fusion model feature schema mismatch."
        )


    top_k = int(
        top_k
    )


    if top_k < 1:

        raise ValueError(
            "top_k must be >= 1."
        )


    top_k = min(
        top_k,
        len(
            FUSION_FEATURE_NAMES
        ),
    )


    vector = extract_fusion_vector(
        fused_features
    )


    mean = np.asarray(
        fusion_model.scaler_mean,
        dtype=np.float64,
    )

    scale = np.asarray(
        fusion_model.scaler_scale,
        dtype=np.float64,
    )

    weights = np.asarray(
        fusion_model.weights,
        dtype=np.float64,
    )


    expected_shape = (
        len(
            FUSION_FEATURE_NAMES
        ),
    )


    if (
        mean.shape
        != expected_shape
        or scale.shape
        != expected_shape
        or weights.shape
        != expected_shape
    ):

        raise ValueError(
            "Fusion model parameter length mismatch."
        )


    if not np.all(
        np.isfinite(
            mean
        )
    ):

        raise ValueError(
            "Fusion scaler mean contains non-finite values."
        )


    if not np.all(
        np.isfinite(
            scale
        )
    ):

        raise ValueError(
            "Fusion scaler scale contains non-finite values."
        )


    if not np.all(
        scale > 0.0
    ):

        raise ValueError(
            "Fusion scaler scale must be positive."
        )


    if not np.all(
        np.isfinite(
            weights
        )
    ):

        raise ValueError(
            "Fusion weights contain non-finite values."
        )


    standardized = (
        vector
        - mean
    ) / scale


    contributions = (
        standardized
        * weights
    )


    bias = float(
        fusion_model.bias
    )


    logit = (
        float(
            np.sum(
                contributions
            )
        )
        + bias
    )


    reconstructed_probability = (
        _sigmoid_scalar(
            logit
        )
    )


    model_probability = float(
        fusion_model.predict_proba_matrix(
            vector.reshape(
                1,
                -1,
            )
        )[0]
    )


    probability_error = abs(
        reconstructed_probability
        - model_probability
    )


    rows = []


    modality_totals = {
        "vision":
            0.0,

        "sensor":
            0.0,

        "temporal":
            0.0,
    }


    for (
        name,
        raw_value,
        standardized_value,
        weight,
        contribution,
    ) in zip(
        FUSION_FEATURE_NAMES,
        vector,
        standardized,
        weights,
        contributions,
    ):

        prefix = name.split(
            "__",
            1,
        )[0]


        if prefix not in modality_totals:

            raise ValueError(
                "Unsupported fusion feature modality."
            )


        modality_totals[
            prefix
        ] += float(
            contribution
        )


        rows.append(
            {
                "feature":
                    name,

                "modality":
                    prefix,

                "raw_value":
                    float(
                        raw_value
                    ),

                "standardized_value":
                    float(
                        standardized_value
                    ),

                "weight":
                    float(
                        weight
                    ),

                "logit_contribution":
                    float(
                        contribution
                    ),

                "absolute_logit_contribution":
                    abs(
                        float(
                            contribution
                        )
                    ),
            }
        )


    ranked = sorted(
        rows,
        key=lambda item: (
            -item[
                "absolute_logit_contribution"
            ],
            item[
                "feature"
            ],
        ),
    )


    return {
        "status":
            "AVAILABLE",

        "method":
            "EXACT_STANDARDIZED_LINEAR_LOGIT_DECOMPOSITION",

        "model_schema_version":
            fusion_model.model_schema_version,

        "feature_vector_version":
            fusion_model.feature_vector_version,

        "feature_count":
            len(
                FUSION_FEATURE_NAMES
            ),

        "bias":
            bias,

        "reconstructed_logit":
            float(
                logit
            ),

        "reconstructed_probability":
            float(
                reconstructed_probability
            ),

        "model_probability":
            float(
                model_probability
            ),

        "probability_reconstruction_error":
            float(
                probability_error
            ),

        "probability_reconstruction_match":
            bool(
                probability_error
                <= 1e-12
            ),

        "modality_logit_contributions": {
            key:
                float(
                    value
                )
            for key, value
            in modality_totals.items()
        },

        "top_feature_contributions":
            ranked[
                :top_k
            ],

        "interpretation": {
            "positive_contribution":
                (
                    "Pushes this logistic model's logit "
                    "toward the positive class."
                ),

            "negative_contribution":
                (
                    "Pushes this logistic model's logit "
                    "away from the positive class."
                ),

            "causal_importance":
                False,

            "global_feature_importance":
                False,

            "real_world_validity_claimed":
                False,
        },

        "scientific_guardrails": {
            "contribution_is_model_specific":
                True,

            "contribution_is_causal":
                False,

            "fusion_model_real_world_validated":
                False,

            "operational_water_stress_explanation":
                False,

            "physical_action_authorized":
                False,
        },
    }


def build_decision_explanation(
    *,
    decision_result: Mapping[
        str,
        Any,
    ],
    reason_flags: Mapping[
        str,
        Any,
    ],
    fusion_model: Optional[
        MultimodalFusionModel
    ] = None,
    fused_features: Optional[
        Mapping[str, Any]
    ] = None,
    top_k: int = 8,
) -> dict[str, Any]:

    (
        decision,
        internal_reason_codes,
    ) = _normalize_decision(
        decision_result
    )


    normalized_flags = (
        _normalize_reason_flags(
            reason_flags
        )
    )


    standard_reasons = [
        code
        for code in STANDARD_REASON_CODES
        if normalized_flags[
            code
        ]
    ]


    if standard_reasons:

        explanation = (
            f"Decision: {decision}. "
            + " ".join(
                REASON_TEXT[
                    code
                ]
                for code
                in standard_reasons
            )
        )

    else:

        explanation = (
            f"Decision: {decision}. "
            "No standardized reason flag was active."
        )


    if (
        fusion_model is None
        and fused_features is None
    ):

        contributions = {
            "status":
                "NOT_AVAILABLE",

            "reason":
                "FUSION_MODEL_AND_FEATURES_NOT_PROVIDED",

            "scientific_guardrails": {
                "feature_importance_invented":
                    False,

                "physical_action_authorized":
                    False,
            },
        }


    elif (
        fusion_model is None
        or fused_features is None
    ):

        raise ValueError(
            "fusion_model and fused_features "
            "must be supplied together."
        )


    else:

        contributions = (
            calculate_fusion_contributions(
                fusion_model=
                    fusion_model,

                fused_features=
                    fused_features,

                top_k=
                    top_k,
            )
        )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "decision":
            decision,

        "standard_reason_codes":
            standard_reasons,

        "decision_internal_reason_codes":
            internal_reason_codes,

        "human_readable_explanation":
            explanation,

        "explanation_generation": {
            "method":
                "DETERMINISTIC_TEMPLATE",

            "llm_used":
                False,

            "control_hot_path_safe":
                True,
        },

        "fusion_explainability":
            contributions,

        "scientific_guardrails": {
            "raw_numeric_thresholds_inferred_here":
                False,

            "reason_flags_must_come_from_upstream_logic":
                True,

            "disease_confidence_reinterpreted_as_water_stress":
                False,

            "llm_used_in_control_hot_path":
                False,

            "causal_feature_importance_claimed":
                False,

            "real_multimodal_explainability_validated":
                False,

            "physical_action_authorized":
                False,
        },
    }
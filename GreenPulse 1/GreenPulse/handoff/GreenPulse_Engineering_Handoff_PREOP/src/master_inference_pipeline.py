from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.image_quality import (
    check_image_quality,
)

from src.visual_features import (
    extract_visual_features,
)

from src.sensor_validator import (
    validate_sensor,
)

from src.sensor_feature_engineering import (
    build_sensor_feature_vector,
)

from src.time_sync import (
    synchronize,
)

from src.feature_fusion import (
    build_multimodal_feature_vector,
)

from src.stress_risk_score import (
    blocked_stress_risk_score,
)

from src.ai_uncertainty import (
    evaluate_uncertainty,
)

from src.vision_sensor_conflict import (
    evaluate_vision_sensor_conflict,
)

from src.decision_intelligence import (
    evaluate_decision,
)

from src.decision_safety import (
    evaluate_decision_safety,
)

from src.decision_explainability import (
    build_decision_explanation,
)

from src.safety_gate import (
    evaluate_safety,
)


PIPELINE_VERSION = (
    "greenpulse.master_ai_inference_pipeline.v1"
)

OUTPUT_SCHEMA_VERSION = (
    "greenpulse.master_observation_output.v1"
)


STAGE_ORDER = (
    "IMAGE_QUALITY",
    "PREPROCESSING",
    "VISION_INFERENCE",
    "VISUAL_FEATURES",
    "SENSOR_VALIDATION",
    "SENSOR_FEATURES",
    "TIME_SYNC",
    "MULTIMODAL_FEATURE_FUSION",
    "MULTIMODAL_MODEL",
    "STRESS_RISK",
    "TEMPORAL_INTELLIGENCE",
    "FORECAST",
    "UNCERTAINTY",
    "VISION_SENSOR_CONFLICT",
    "DECISION",
    "DECISION_SAFETY",
    "EXPLAINABILITY",
)


def _require_string(
    value: Any,
    name: str,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):

        raise ValueError(
            f"{name} is required."
        )

    return value.strip()


def _blocked_stage(
    reason: str,
) -> dict[str, Any]:

    return {
        "status":
            "BLOCKED",

        "reason":
            str(
                reason
            ),
    }


def _unavailable_stage(
    reason: str,
) -> dict[str, Any]:

    return {
        "status":
            "UNAVAILABLE",

        "reason":
            str(
                reason
            ),
    }


def _vision_classification(
    result: Mapping[
        str,
        Any,
    ],
) -> tuple[
    Optional[float],
    Optional[str],
]:

    if not isinstance(
        result,
        Mapping,
    ):

        return None, None


    if result.get(
        "status"
    ) != "SUCCESS":

        return None, None


    vision = result.get(
        "vision"
    )


    if not isinstance(
        vision,
        Mapping,
    ):

        return None, None


    confidence = vision.get(
        "confidence"
    )


    if confidence is None:

        return None, None


    confidence = float(
        confidence
    )


    if not (
        0.0
        <= confidence
        <= 1.0
    ):

        raise ValueError(
            "Vision confidence must be in [0, 1]."
        )


    return (
        confidence,
        "classification",
    )


def _reason_flags(
    *,
    uncertainty: Mapping[
        str,
        Any,
    ],
    image_quality: Mapping[
        str,
        Any,
    ],
    sensor_status: str,
    conflict: Mapping[
        str,
        Any,
    ],
) -> dict[str, bool]:

    uncertainty_reasons = set(
        uncertainty.get(
            "reason_codes",
            [],
        )
    )


    return {
        "VISUAL_STRESS_HIGH":
            False,

        "VISUAL_DELTA_HIGH":
            False,

        "LOW_SOIL_MOISTURE":
            False,

        "HIGH_TEMPERATURE":
            False,

        "RISK_TREND_RISING":
            False,

        "FORECAST_RISK_RISING":
            False,

        "TEMPORAL_CONFIRMATION":
            False,

        "LOW_CONFIDENCE":
            (
                "LOW_CONFIDENCE"
                in uncertainty_reasons
            ),

        "IMAGE_QUALITY_LOW":
            (
                image_quality.get(
                    "status"
                )
                != "IMAGE_OK"
            ),

        "SENSOR_DATA_INVALID":
            (
                sensor_status
                != "VALID"
            ),

        "VISION_SENSOR_CONFLICT":
            bool(
                conflict.get(
                    "vision_sensor_conflict",
                    False,
                )
            ),
    }


def run_master_inference_pipeline(
    *,
    observation_id: str,
    plant_id: str,
    crop: str,
    image_path: Any,
    image_captured_at: str,
    sensor_packet: Mapping[
        str,
        Any,
    ],
    sensor_observations: Sequence[
        Mapping[str, Any]
    ],
    vision_engine: Optional[Any] = None,
    plant_baseline: Optional[
        Mapping[str, Any]
    ] = None,
    sensor_baseline: Optional[
        Mapping[str, Any]
    ] = None,
    sensor_normalization_artifact: Optional[
        Mapping[str, Any]
    ] = None,
    prior_temporal_features: Optional[
        Mapping[str, Any]
    ] = None,
    fusion_model: Optional[Any] = None,
    forecast_model: Optional[Any] = None,
    confidence_threshold: Optional[
        float
    ] = None,
    confidence_threshold_validated: bool = False,
    vision_stress_state: str = "UNKNOWN",
    vision_stress_validated: bool = False,
    sensor_stress_state: str = "UNKNOWN",
    sensor_stress_validated: bool = False,
    manual_override: str = "NONE",
) -> dict[str, Any]:

    observation_id = _require_string(
        observation_id,
        "observation_id",
    )

    plant_id = _require_string(
        plant_id,
        "plant_id",
    )

    crop = _require_string(
        crop,
        "crop",
    )

    image_captured_at = (
        _require_string(
            image_captured_at,
            "image_captured_at",
        )
    )


    image_path = Path(
        image_path
    )


    if not image_path.is_file():

        raise FileNotFoundError(
            image_path
        )


    if not isinstance(
        sensor_packet,
        Mapping,
    ):

        raise ValueError(
            "sensor_packet must be a mapping."
        )


    if (
        sensor_packet.get(
            "plant_id"
        )
        != plant_id
    ):

        raise ValueError(
            "sensor_packet plant_id mismatch."
        )


    if not isinstance(
        sensor_observations,
        Sequence,
    ):

        raise ValueError(
            "sensor_observations must be a sequence."
        )


    stages = {}


    # -------------------------------------------------
    # 1. IMAGE QUALITY
    # -------------------------------------------------

    image_bytes = (
        image_path.read_bytes()
    )

    image_quality = (
        check_image_quality(
            image_bytes
        )
    )

    stages[
        "image_quality"
    ] = image_quality


    # -------------------------------------------------
    # 2. PREPROCESSING
    # -------------------------------------------------

    preprocessing = {
        "status":
            (
                "READY"
                if image_quality.get(
                    "eligible_for_inference"
                ) is True
                else "BLOCKED"
            ),

        "implementation":
            (
                "Existing vision and visual-feature "
                "contracts own decode/RGB/resize/"
                "normalization as applicable."
            ),

        "separate_new_preprocessor_in_layer35":
            False,
    }

    stages[
        "preprocessing"
    ] = preprocessing


    # -------------------------------------------------
    # 3. SENSOR VALIDATION
    # -------------------------------------------------

    (
        sensor_status,
        sensor_reason,
    ) = validate_sensor(
        dict(
            sensor_packet
        )
    )


    sensor_validation = {
        "status":
            sensor_status,

        "reason":
            sensor_reason,
    }


    stages[
        "sensor_validation"
    ] = sensor_validation


    # -------------------------------------------------
    # 4. TIME SYNC
    # -------------------------------------------------

    sensor_timestamp = (
        sensor_packet.get(
            "timestamp"
        )
    )


    time_sync = synchronize(
        image_captured_at,
        sensor_timestamp,
    )


    stages[
        "time_sync"
    ] = time_sync


    # -------------------------------------------------
    # 5. VISION INFERENCE
    # -------------------------------------------------

    vision_inference = None

    vision_confidence = None

    confidence_source = None


    if (
        image_quality.get(
            "eligible_for_inference"
        )
        is not True
    ):

        vision_inference = (
            _blocked_stage(
                "IMAGE_QUALITY_GATE_FAILED"
            )
        )


    elif vision_engine is None:

        vision_inference = (
            _blocked_stage(
                "VISION_ENGINE_NOT_PROVIDED"
            )
        )


    else:

        predictor = getattr(
            vision_engine,
            "predict",
            None,
        )


        if not callable(
            predictor
        ):

            raise ValueError(
                "vision_engine must provide predict()."
            )


        try:

            vision_inference = predictor(
                image_path,
                crop,
            )

        except Exception as exc:

            vision_inference = {
                "status":
                    "INFERENCE_ERROR",

                "error_type":
                    type(
                        exc
                    ).__name__,
            }


        if isinstance(
            vision_inference,
            Mapping,
        ):

            (
                vision_confidence,
                confidence_source,
            ) = _vision_classification(
                vision_inference
            )


    stages[
        "vision_inference"
    ] = vision_inference


    # -------------------------------------------------
    # 6. VISUAL FEATURES
    # -------------------------------------------------

    visual_features = None


    if (
        vision_confidence
        is None
        or confidence_source
        is None
    ):

        visual_features = (
            _blocked_stage(
                "VALID_VISION_CLASSIFICATION_REQUIRED"
            )
        )


    else:

        visual_features = (
            extract_visual_features(
                image_path,
                visual_confidence=
                    vision_confidence,
                confidence_source=
                    confidence_source,
            )
        )


    stages[
        "visual_features"
    ] = visual_features


    # -------------------------------------------------
    # 7. PLANT DELTA
    #
    # Layer35 does not manufacture a baseline/delta.
    # A validated upstream delta is not fabricated here.
    # -------------------------------------------------

    plant_delta = None


    if plant_baseline is None:

        plant_delta_stage = (
            _unavailable_stage(
                "PLANT_BASELINE_NOT_PROVIDED"
            )
        )

    else:

        # Deliberately not recomputed here because
        # Layer35 has no right to silently assume the
        # baseline is healthy/validated. Baseline/Delta
        # Layer owns that evidence.
        plant_delta_stage = (
            _blocked_stage(
                "VALIDATED_PLANT_DELTA_MUST_BE_PROVIDED_BY_BASELINE_LAYER"
            )
        )


    stages[
        "plant_delta"
    ] = plant_delta_stage


    # -------------------------------------------------
    # 8. SENSOR FEATURES
    # -------------------------------------------------

    sensor_features = None


    if sensor_status not in {
        "VALID",
        "VALID_SIMULATED",
    }:

        sensor_features = (
            _blocked_stage(
                "CURRENT_SENSOR_PACKET_NOT_VALID"
            )
        )


    else:

        sensor_features = (
            build_sensor_feature_vector(
                sensor_packet,
                sensor_observations,
                baseline=
                    sensor_baseline,
                normalization_artifact=
                    sensor_normalization_artifact,
            )
        )


    stages[
        "sensor_features"
    ] = sensor_features


    # -------------------------------------------------
    # 9. MULTIMODAL FEATURE FUSION
    # -------------------------------------------------

    fused_features = None


    can_build_fusion = (
        isinstance(
            visual_features,
            Mapping,
        )
        and visual_features.get(
            "feature_vector_version"
        )
        is not None
        and isinstance(
            sensor_features,
            Mapping,
        )
        and sensor_features.get(
            "feature_vector_version"
        )
        is not None
        and time_sync.get(
            "status"
        )
        == "SYNCED"
    )


    if can_build_fusion:

        fused_features = (
            build_multimodal_feature_vector(
                visual_features=
                    visual_features,
                sensor_features=
                    sensor_features,
                plant_delta=
                    plant_delta,
                temporal_features=
                    prior_temporal_features,
                time_sync_status=
                    "SYNCED",
            )
        )

    else:

        fused_features = (
            _blocked_stage(
                "FUSION_PREREQUISITES_NOT_SATISFIED"
            )
        )


    stages[
        "multimodal_feature_fusion"
    ] = fused_features


    # -------------------------------------------------
    # 10. MULTIMODAL MODEL
    # -------------------------------------------------

    fusion_prediction = None


    if (
        fusion_model is None
    ):

        fusion_prediction = (
            _blocked_stage(
                "REAL_MULTIMODAL_FUSION_MODEL_NOT_AVAILABLE"
            )
        )


    elif not (
        isinstance(
            fused_features,
            Mapping,
        )
        and fused_features.get(
            "feature_vector_version"
        )
        is not None
    ):

        fusion_prediction = (
            _blocked_stage(
                "FUSED_FEATURE_VECTOR_UNAVAILABLE"
            )
        )


    else:

        predictor = getattr(
            fusion_model,
            "predict_record",
            None,
        )


        if not callable(
            predictor
        ):

            raise ValueError(
                "fusion_model must provide predict_record()."
            )


        fusion_prediction = (
            predictor(
                fused_features
            )
        )


    stages[
        "multimodal_model"
    ] = fusion_prediction


    # -------------------------------------------------
    # 11. STRESS RISK
    #
    # No real validated calibration artifact is
    # currently available. Raw fusion probability is
    # never promoted to an operational stress score.
    # -------------------------------------------------

    feature_version = (
        fused_features.get(
            "feature_vector_version"
        )
        if isinstance(
            fused_features,
            Mapping,
        )
        else "UNAVAILABLE"
    )


    model_version = (
        fusion_prediction.get(
            "model_schema_version"
        )
        if isinstance(
            fusion_prediction,
            Mapping,
        )
        and fusion_prediction.get(
            "model_schema_version"
        )
        else "UNAVAILABLE_MULTIMODAL_FUSION_MODEL"
    )


    risk = blocked_stress_risk_score(
        reason=(
            "VALIDATED_CALIBRATED_MULTIMODAL_"
            "PROBABILITY_NOT_AVAILABLE"
        ),
        model_version=
            str(
                model_version
            ),
        feature_vector_version=
            str(
                feature_version
            ),
        timestamp=
            str(
                sensor_timestamp
            ),
    )


    stages[
        "stress_risk"
    ] = risk


    # -------------------------------------------------
    # 12. TEMPORAL INTELLIGENCE
    #
    # Current observation has no operational risk score,
    # so Layer35 must not fabricate a temporal update.
    # -------------------------------------------------

    temporal = (
        _blocked_stage(
            "CURRENT_OPERATIONAL_RISK_SCORE_UNAVAILABLE"
        )
    )


    stages[
        "temporal_intelligence"
    ] = temporal


    # -------------------------------------------------
    # 13. FORECAST
    # -------------------------------------------------

    if forecast_model is None:

        forecast = {
            "status":
                "BLOCKED_FORECAST_MODEL_NOT_OPERATIONALLY_VALIDATED",

            "validated":
                False,

            "future_risk":
                None,

            "naive_future_risk":
                None,

            "physical_action_authorized":
                False,
        }


    else:

        # Even if a model object is supplied, the
        # current operational risk is blocked.
        forecast = {
            "status":
                "BLOCKED_CURRENT_RISK_UNAVAILABLE",

            "validated":
                False,

            "future_risk":
                None,

            "naive_future_risk":
                None,

            "physical_action_authorized":
                False,
        }


    stages[
        "forecast"
    ] = forecast


    # -------------------------------------------------
    # 14. UNCERTAINTY
    # -------------------------------------------------

    inference_error = (
        isinstance(
            vision_inference,
            Mapping,
        )
        and vision_inference.get(
            "status"
        )
        == "INFERENCE_ERROR"
    )


    uncertainty = (
        evaluate_uncertainty(
            model_confidence=
                vision_confidence,

            model_confidence_source=
                confidence_source,

            low_confidence_threshold=
                confidence_threshold,

            confidence_threshold_validated=
                confidence_threshold_validated,

            image_quality=
                image_quality,

            sensor_validation=(
                sensor_status,
                sensor_reason,
            ),

            inference_error=
                inference_error,

            ood_suspected=
                False,

            unusual_feature_combination=
                False,
        )
    )


    stages[
        "uncertainty"
    ] = uncertainty


    # -------------------------------------------------
    # 15. VISION / SENSOR CONFLICT
    #
    # Disease classification is NOT converted into
    # water-stress state. Defaults remain UNKNOWN.
    # -------------------------------------------------

    conflict = (
        evaluate_vision_sensor_conflict(
            vision_state=
                vision_stress_state,

            sensor_state=
                sensor_stress_state,

            vision_source=
                "UPSTREAM_VALIDATED_STRESS_SIGNAL"
                if vision_stress_validated
                else "NO_VALIDATED_WATER_STRESS_VISION_SIGNAL",

            sensor_source=
                "UPSTREAM_VALIDATED_STRESS_SIGNAL"
                if sensor_stress_validated
                else "NO_VALIDATED_SENSOR_STRESS_STATE",

            vision_signal_validated=
                vision_stress_validated,

            sensor_signal_validated=
                sensor_stress_validated,
        )
    )


    stages[
        "vision_sensor_conflict"
    ] = conflict


    # -------------------------------------------------
    # 16. EXISTING CONSERVATIVE SAFETY GATE
    # -------------------------------------------------

    existing_safety = (
        evaluate_safety(
            {
                "sensor": {
                    "status":
                        sensor_status,
                },

                "image_capture": {
                    # Layer35 does not claim device-level
                    # capture authenticity merely because
                    # a timestamp string was provided.
                    "verified":
                        False,
                },

                "time_sync":
                    time_sync,
            }
        )
    )


    # -------------------------------------------------
    # 17. DECISION
    # -------------------------------------------------

    decision = (
        evaluate_decision(
            vision_result={
                "state":
                    vision_stress_state,

                "validated":
                    vision_stress_validated,

                "vision_sensor_conflict":
                    bool(
                        conflict.get(
                            "vision_sensor_conflict",
                            False,
                        )
                    ),
            },

            fusion_risk={
                "band":
                    "UNKNOWN",

                "thresholds_validated":
                    False,

                "stress_risk_score":
                    None,
            },

            forecast=
                forecast,

            temporal_consistency={
                "state":
                    "RECHECK",
            },

            uncertainty=
                uncertainty,

            sensor_validity=(
                sensor_status,
                sensor_reason,
            ),

            safety_state=
                existing_safety,
        )
    )


    stages[
        "decision"
    ] = decision


    # -------------------------------------------------
    # 18. DECISION SAFETY
    # -------------------------------------------------

    decision_safety = (
        evaluate_decision_safety(
            decision_result=
                decision,

            safety_context={
                "model_confidence":
                    vision_confidence,

                "stress_risk_score":
                    None,

                "confirmation_count":
                    None,

                "seconds_since_last_request":
                    None,

                "requested_action_duration_seconds":
                    None,

                "camera_valid":
                    (
                        image_quality.get(
                            "eligible_for_inference"
                        )
                        is True
                    ),

                "sensor_valid":
                    (
                        sensor_status
                        == "VALID"
                    ),

                "manual_override":
                    manual_override,
            },

            test_only=
                False,
        )
    )


    stages[
        "decision_safety"
    ] = decision_safety


    # -------------------------------------------------
    # 19. EXPLAINABILITY
    # -------------------------------------------------

    reason_flags = _reason_flags(
        uncertainty=
            uncertainty,

        image_quality=
            image_quality,

        sensor_status=
            sensor_status,

        conflict=
            conflict,
    )


    explanation = (
        build_decision_explanation(
            decision_result=
                decision,

            reason_flags=
                reason_flags,
        )
    )


    stages[
        "explainability"
    ] = explanation


    # -------------------------------------------------
    # FINAL VERSIONED OBSERVATION OUTPUT
    # -------------------------------------------------

    return {
        "schema_version":
            OUTPUT_SCHEMA_VERSION,

        "pipeline_version":
            PIPELINE_VERSION,

        "observation_id":
            observation_id,

        "plant_id":
            plant_id,

        "crop":
            crop,

        "image_captured_at":
            image_captured_at,

        "sensor_timestamp":
            sensor_timestamp,

        "stage_order":
            list(
                STAGE_ORDER
            ),

        "stages":
            stages,

        "final": {
            "decision":
                decision.get(
                    "decision"
                ),

            "decision_reason_codes":
                decision.get(
                    "reason_codes",
                    [],
                ),

            "safety_status":
                decision_safety.get(
                    "status"
                ),

            "human_readable_explanation":
                explanation.get(
                    "human_readable_explanation"
                ),

            "stress_risk_score":
                None,

            "forecast":
                None,

            "hardware_dispatch_permitted":
                False,

            "physical_actuation":
                False,
        },

        "operational_readiness": {
            "real_multimodal_stress_model":
                False,

            "validated_risk_calibration":
                False,

            "validated_operational_thresholds":
                False,

            "validated_real_forecast":
                False,

            "validated_operational_safety_policy":
                False,

            "real_autonomous_irrigation":
                False,
        },

        "scientific_guardrails": {
            "disease_classification_is_water_stress":
                False,

            "classification_confidence_used_as_operational_stress_probability":
                False,

            "raw_fusion_probability_promoted_to_risk":
                False,

            "simulated_sensor_is_real_sensor_evidence":
                False,

            "sensor_source_field_is_device_authentication":
                False,

            "unvalidated_thresholds_invented":
                False,

            "blocked_stage_silently_promoted":
                False,

            "physical_action_authorized":
                False,
        },
    }
from __future__ import annotations

from typing import Any, Mapping, Optional

import math


SCHEMA_VERSION = (
    "greenpulse.standard_ai_output.v1"
)

NULL_POLICY_VERSION = (
    "greenpulse.standard_ai_output_null_policy.v1"
)


NULL_FALLBACK_POLICY = {
    "timestamp":
        (
            "MASTER: sensor_timestamp, then image_captured_at. "
            "LEGACY: timestamp. NULL only when no source timestamp exists."
        ),

    "vision.output":
        (
            "NULL when no structured vision output is available."
        ),

    "sensor.snapshot":
        (
            "NULL when no validated/current sensor snapshot is available."
        ),

    "risk":
        (
            "Preserve structured BLOCKED/UNAVAILABLE risk objects. "
            "NULL only when the source has no risk object."
        ),

    "trend":
        (
            "NULL when validated temporal risk dynamics are unavailable. "
            "Sensor-window statistics are not reinterpreted as risk trend."
        ),

    "forecast":
        (
            "Preserve structured BLOCKED/UNAVAILABLE forecast objects. "
            "NULL only when no forecast object exists."
        ),

    "uncertainty":
        (
            "NULL when the source contract has no uncertainty result."
        ),

    "model_versions":
        (
            "Each unavailable model/version entry is explicitly NULL."
        ),

    "latency.total_ms":
        (
            "NULL unless measured latency is supplied by the caller."
        ),
}


def _mapping_or_none(
    value: Any,
) -> Optional[dict[str, Any]]:

    if isinstance(
        value,
        Mapping,
    ):

        return dict(
            value
        )

    return None


def _string_or_none(
    value: Any,
) -> Optional[str]:

    if (
        isinstance(
            value,
            str,
        )
        and value.strip()
    ):

        return value.strip()

    return None


def _latency_contract(
    latency_ms: Optional[Any],
) -> dict[str, Any]:

    if latency_ms is None:

        return {
            "total_ms":
                None,

            "measured":
                False,

            "source":
                "NOT_MEASURED",
        }


    if (
        isinstance(
            latency_ms,
            bool,
        )
        or not isinstance(
            latency_ms,
            (int, float),
        )
    ):

        raise ValueError(
            "latency_ms must be a finite non-negative number."
        )


    value = float(
        latency_ms
    )


    if (
        not math.isfinite(
            value
        )
        or value < 0.0
    ):

        raise ValueError(
            "latency_ms must be a finite non-negative number."
        )


    return {
        "total_ms":
            value,

        "measured":
            True,

        "source":
            "CALLER_MEASURED",
    }


def _timestamp_from_master(
    payload: Mapping[
        str,
        Any,
    ],
) -> tuple[
    Optional[str],
    str,
]:

    sensor_timestamp = (
        _string_or_none(
            payload.get(
                "sensor_timestamp"
            )
        )
    )


    if sensor_timestamp is not None:

        return (
            sensor_timestamp,
            "SENSOR_TIMESTAMP",
        )


    image_timestamp = (
        _string_or_none(
            payload.get(
                "image_captured_at"
            )
        )
    )


    if image_timestamp is not None:

        return (
            image_timestamp,
            "IMAGE_CAPTURED_AT",
        )


    return (
        None,
        "UNAVAILABLE",
    )


def _decision_from_mapping(
    value: Any,
) -> tuple[
    Optional[str],
    list[str],
]:

    if isinstance(
        value,
        str,
    ):

        return (
            value,
            [],
        )


    if not isinstance(
        value,
        Mapping,
    ):

        return (
            None,
            [],
        )


    decision = (
        value.get(
            "decision"
        )
        or value.get(
            "action"
        )
    )


    reasons = value.get(
        "reason_codes",
        [],
    )


    if not isinstance(
        reasons,
        list,
    ):

        reasons = []


    return (
        str(
            decision
        )
        if decision is not None
        else None,

        [
            str(
                item
            )
            for item
            in reasons
        ],
    )


def _from_master(
    payload: Mapping[
        str,
        Any,
    ],
    *,
    latency_ms: Optional[Any],
) -> dict[str, Any]:

    stages = payload.get(
        "stages"
    )


    if not isinstance(
        stages,
        Mapping,
    ):

        raise ValueError(
            "Master pipeline output requires stages mapping."
        )


    final = payload.get(
        "final"
    )


    if not isinstance(
        final,
        Mapping,
    ):

        raise ValueError(
            "Master pipeline output requires final mapping."
        )


    timestamp, timestamp_source = (
        _timestamp_from_master(
            payload
        )
    )


    vision_stage = (
        _mapping_or_none(
            stages.get(
                "vision_inference"
            )
        )
    )


    vision_output = None

    vision_model = None

    vision_status = None


    if vision_stage is not None:

        vision_status = (
            vision_stage.get(
                "status"
            )
        )

        vision_output = (
            _mapping_or_none(
                vision_stage.get(
                    "vision"
                )
            )
        )

        vision_model = (
            _mapping_or_none(
                vision_stage.get(
                    "model"
                )
            )
        )


    sensor_validation = (
        _mapping_or_none(
            stages.get(
                "sensor_validation"
            )
        )
        or {}
    )


    sensor_features = (
        _mapping_or_none(
            stages.get(
                "sensor_features"
            )
        )
    )


    sensor_snapshot = None


    if sensor_features is not None:

        sensor_snapshot = (
            _mapping_or_none(
                sensor_features.get(
                    "current"
                )
            )
        )


    risk = (
        _mapping_or_none(
            stages.get(
                "stress_risk"
            )
        )
    )


    temporal = (
        _mapping_or_none(
            stages.get(
                "temporal_intelligence"
            )
        )
    )


    trend = None


    if temporal is not None:

        trend = (
            _mapping_or_none(
                temporal.get(
                    "risk_dynamics"
                )
            )
        )


    forecast = (
        _mapping_or_none(
            stages.get(
                "forecast"
            )
        )
    )


    uncertainty = (
        _mapping_or_none(
            stages.get(
                "uncertainty"
            )
        )
    )


    decision_stage = (
        _mapping_or_none(
            stages.get(
                "decision"
            )
        )
    )


    decision = (
        final.get(
            "decision"
        )
    )


    reasons = final.get(
        "decision_reason_codes",
        [],
    )


    if not isinstance(
        reasons,
        list,
    ):

        reasons = []


    if decision is None:

        (
            decision,
            reasons,
        ) = _decision_from_mapping(
            decision_stage
        )


    multimodal_stage = (
        _mapping_or_none(
            stages.get(
                "multimodal_model"
            )
        )
    )


    safety_stage = (
        _mapping_or_none(
            stages.get(
                "decision_safety"
            )
        )
    )


    model_versions = {
        "pipeline":
            _string_or_none(
                payload.get(
                    "pipeline_version"
                )
            ),

        "vision":
            (
                _string_or_none(
                    vision_model.get(
                        "version"
                    )
                )
                if vision_model
                is not None
                else None
            ),

        "multimodal_fusion":
            (
                _string_or_none(
                    multimodal_stage.get(
                        "model_version"
                    )
                )
                if multimodal_stage
                is not None
                else None
            ),

        "stress_risk_model":
            (
                _string_or_none(
                    risk.get(
                        "model_version"
                    )
                )
                if risk
                is not None
                else None
            ),

        "forecast":
            (
                _string_or_none(
                    forecast.get(
                        "model_version"
                    )
                )
                if forecast
                is not None
                else None
            ),

        "decision":
            (
                _string_or_none(
                    decision_stage.get(
                        "decision_version"
                    )
                )
                if decision_stage
                is not None
                else None
            ),

        "safety_policy":
            (
                _string_or_none(
                    safety_stage.get(
                        "policy_version"
                    )
                )
                if safety_stage
                is not None
                else None
            ),
    }


    risk_score_available = (
        risk is not None
        and risk.get(
            "stress_risk_score"
        )
        is not None
    )


    trend_available = (
        trend is not None
    )


    forecast_available = (
        forecast is not None
        and forecast.get(
            "future_risk"
        )
        is not None
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "observation_id":
            payload.get(
                "observation_id"
            ),

        "plant_id":
            payload.get(
                "plant_id"
            ),

        "timestamp":
            timestamp,

        "timestamp_source":
            timestamp_source,

        "crop":
            payload.get(
                "crop"
            ),

        "vision": {
            "status":
                vision_status,

            "output":
                vision_output,

            "model":
                vision_model,
        },

        "sensor": {
            "status":
                sensor_validation.get(
                    "status"
                ),

            "reason":
                sensor_validation.get(
                    "reason"
                ),

            "snapshot":
                sensor_snapshot,

            "snapshot_available":
                sensor_snapshot
                is not None,

            "device_authenticated":
                False,
        },

        "risk":
            risk,

        "trend":
            trend,

        "forecast":
            forecast,

        "uncertainty":
            uncertainty,

        "decision":
            decision,

        "reason_codes":
            [
                str(
                    item
                )
                for item
                in reasons
            ],

        "model_versions":
            model_versions,

        "latency":
            _latency_contract(
                latency_ms
            ),

        "field_availability": {
            "vision_output":
                vision_output
                is not None,

            "sensor_snapshot":
                sensor_snapshot
                is not None,

            "risk_score":
                risk_score_available,

            "trend":
                trend_available,

            "forecast_value":
                forecast_available,

            "uncertainty":
                uncertainty
                is not None,
        },

        "contract_metadata": {
            "source_contract":
                "MASTER_AI_INFERENCE_PIPELINE",

            "source_schema_version":
                payload.get(
                    "schema_version"
                ),

            "null_policy_version":
                NULL_POLICY_VERSION,

            "null_fallback_policy":
                dict(
                    NULL_FALLBACK_POLICY
                ),
        },

        "scientific_guardrails": {
            "disease_classification_is_water_stress":
                False,

            "missing_risk_invented":
                False,

            "missing_trend_invented":
                False,

            "missing_forecast_invented":
                False,

            "missing_latency_invented":
                False,

            "sensor_source_is_device_authentication":
                False,

            "physical_action_authorized":
                False,
        },
    }


def _from_legacy(
    payload: Mapping[
        str,
        Any,
    ],
    *,
    latency_ms: Optional[Any],
) -> dict[str, Any]:

    timestamp = (
        _string_or_none(
            payload.get(
                "timestamp"
            )
        )
    )


    vision_output = (
        _mapping_or_none(
            payload.get(
                "vision"
            )
        )
    )


    sensor = (
        _mapping_or_none(
            payload.get(
                "sensor"
            )
        )
        or {}
    )


    decision, reasons = (
        _decision_from_mapping(
            payload.get(
                "decision"
            )
        )
    )


    model = (
        _mapping_or_none(
            payload.get(
                "model"
            )
        )
    )


    risk = (
        _mapping_or_none(
            payload.get(
                "water_stress_risk"
            )
        )
    )


    forecast = (
        _mapping_or_none(
            payload.get(
                "forecast"
            )
        )
    )


    uncertainty = (
        _mapping_or_none(
            payload.get(
                "uncertainty"
            )
        )
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "observation_id":
            payload.get(
                "observation_id"
            ),

        "plant_id":
            payload.get(
                "plant_id"
            ),

        "timestamp":
            timestamp,

        "timestamp_source":
            (
                "OBSERVATION_TIMESTAMP"
                if timestamp
                is not None
                else "UNAVAILABLE"
            ),

        "crop":
            payload.get(
                "crop"
            ),

        "vision": {
            "status":
                (
                    "AVAILABLE"
                    if vision_output
                    is not None
                    else "UNAVAILABLE"
                ),

            "output":
                vision_output,

            "model":
                model,
        },

        "sensor": {
            "status":
                sensor.get(
                    "status"
                ),

            "reason":
                sensor.get(
                    "reason"
                ),

            "snapshot":
                (
                    _mapping_or_none(
                        sensor.get(
                            "data"
                        )
                    )
                ),

            "snapshot_available":
                isinstance(
                    sensor.get(
                        "data"
                    ),
                    Mapping,
                ),

            "device_authenticated":
                False,
        },

        "risk":
            risk,

        # Legacy sensor_window must not be silently
        # relabeled as validated risk trend.
        "trend":
            None,

        "forecast":
            forecast,

        "uncertainty":
            uncertainty,

        "decision":
            decision,

        "reason_codes":
            reasons,

        "model_versions": {
            "pipeline":
                None,

            "vision":
                (
                    _string_or_none(
                        model.get(
                            "version"
                        )
                    )
                    if model
                    is not None
                    else None
                ),

            "multimodal_fusion":
                None,

            "stress_risk_model":
                None,

            "forecast":
                None,

            "decision":
                None,

            "safety_policy":
                None,
        },

        "latency":
            _latency_contract(
                latency_ms
            ),

        "field_availability": {
            "vision_output":
                vision_output
                is not None,

            "sensor_snapshot":
                isinstance(
                    sensor.get(
                        "data"
                    ),
                    Mapping,
                ),

            "risk_score":
                False,

            "trend":
                False,

            "forecast_value":
                (
                    forecast is not None
                    and forecast.get(
                        "future_risk"
                    )
                    is not None
                ),

            "uncertainty":
                uncertainty
                is not None,
        },

        "contract_metadata": {
            "source_contract":
                "LEGACY_API_OBSERVATION",

            "source_schema_version":
                payload.get(
                    "schema_version"
                ),

            "null_policy_version":
                NULL_POLICY_VERSION,

            "null_fallback_policy":
                dict(
                    NULL_FALLBACK_POLICY
                ),
        },

        "scientific_guardrails": {
            "disease_classification_is_water_stress":
                False,

            "legacy_sensor_window_reinterpreted_as_risk_trend":
                False,

            "missing_risk_invented":
                False,

            "missing_trend_invented":
                False,

            "missing_forecast_invented":
                False,

            "missing_uncertainty_invented":
                False,

            "missing_latency_invented":
                False,

            "sensor_source_is_device_authentication":
                False,

            "physical_action_authorized":
                False,
        },
    }


def build_standard_ai_output(
    payload: Mapping[
        str,
        Any,
    ],
    *,
    latency_ms: Optional[Any] = None,
) -> dict[str, Any]:

    if not isinstance(
        payload,
        Mapping,
    ):

        raise ValueError(
            "payload must be a mapping."
        )


    if (
        isinstance(
            payload.get(
                "stages"
            ),
            Mapping,
        )
        and isinstance(
            payload.get(
                "final"
            ),
            Mapping,
        )
    ):

        return _from_master(
            payload,
            latency_ms=
                latency_ms,
        )


    if (
        "vision"
        in payload
        and "sensor"
        in payload
        and "decision"
        in payload
    ):

        return _from_legacy(
            payload,
            latency_ms=
                latency_ms,
        )


    raise ValueError(
        "Unsupported AI output source contract."
    )
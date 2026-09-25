from __future__ import annotations

from typing import Any, Mapping


SCHEMA_VERSION = (
    "greenpulse.vision_sensor_conflict.v1"
)


VALID_MODALITY_STATES = {
    "HIGH_STRESS",
    "NORMAL",
    "UNKNOWN",
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


def _validate_state(
    value: Any,
    name: str,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or value
        not in VALID_MODALITY_STATES
    ):

        raise ValueError(
            f"{name} must be one of "
            "HIGH_STRESS, NORMAL, UNKNOWN."
        )

    return value


def _validate_source(
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


def evaluate_vision_sensor_conflict(
    *,
    vision_state: str,
    sensor_state: str,
    vision_source: str,
    sensor_source: str,
    vision_signal_validated: bool,
    sensor_signal_validated: bool,
) -> dict[str, Any]:

    vision_state = _validate_state(
        vision_state,
        "vision_state",
    )

    sensor_state = _validate_state(
        sensor_state,
        "sensor_state",
    )

    vision_source = _validate_source(
        vision_source,
        "vision_source",
    )

    sensor_source = _validate_source(
        sensor_source,
        "sensor_source",
    )

    vision_signal_validated = _strict_bool(
        vision_signal_validated,
        "vision_signal_validated",
    )

    sensor_signal_validated = _strict_bool(
        sensor_signal_validated,
        "sensor_signal_validated",
    )


    reason_codes = []


    if not vision_signal_validated:

        reason_codes.append(
            "VISION_SIGNAL_NOT_VALIDATED"
        )


    if not sensor_signal_validated:

        reason_codes.append(
            "SENSOR_SIGNAL_NOT_VALIDATED"
        )


    if vision_state == "UNKNOWN":

        reason_codes.append(
            "VISION_STATE_UNKNOWN"
        )


    if sensor_state == "UNKNOWN":

        reason_codes.append(
            "SENSOR_STATE_UNKNOWN"
        )


    evaluable = (
        vision_signal_validated
        and sensor_signal_validated
        and vision_state
        != "UNKNOWN"
        and sensor_state
        != "UNKNOWN"
    )


    conflict = False


    if evaluable:

        conflict = (
            (
                vision_state
                == "HIGH_STRESS"
                and sensor_state
                == "NORMAL"
            )
            or
            (
                vision_state
                == "NORMAL"
                and sensor_state
                == "HIGH_STRESS"
            )
        )


    if conflict:

        status = (
            "VISION_SENSOR_CONFLICT"
        )

        routing = "RECHECK"

        reason_codes.append(
            "MODALITY_CONTRADICTION"
        )


    elif not evaluable:

        status = (
            "CONFLICT_NOT_EVALUABLE"
        )

        routing = "RECHECK"


    else:

        status = "NO_CONFLICT"

        routing = "MONITOR"


    return {
        "schema_version":
            SCHEMA_VERSION,

        "status":
            status,

        "vision_sensor_conflict":
            bool(
                conflict
            ),

        "conflict_evaluable":
            bool(
                evaluable
            ),

        "routing":
            routing,

        "reason_codes":
            reason_codes,

        "vision": {
            "state":
                vision_state,

            "source":
                vision_source,

            "validated":
                vision_signal_validated,
        },

        "sensor": {
            "state":
                sensor_state,

            "source":
                sensor_source,

            "validated":
                sensor_signal_validated,
        },

        "scientific_guardrails": {
            "numeric_thresholds_inferred_here":
                False,

            "disease_classification_confidence_used_as_water_stress":
                False,

            "vision_water_stress_signal_real_world_validated":
                False,

            "sensor_water_stress_conflict_real_world_validated":
                False,

            "conflict_authorizes_forced_actuation":
                False,

            "physical_action_authorized":
                False,
        },
    }
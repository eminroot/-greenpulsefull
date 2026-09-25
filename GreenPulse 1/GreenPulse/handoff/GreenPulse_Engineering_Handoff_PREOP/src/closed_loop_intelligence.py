from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

import math


SCHEMA_VERSION = (
    "greenpulse.closed_loop_intelligence.v1"
)

FOLLOWUP_SCHEMA_VERSION = (
    "greenpulse.closed_loop_followup_plan.v1"
)


def _parse_timestamp(
    value: Any,
    name: str,
) -> datetime:

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


    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    except ValueError as exc:

        raise ValueError(
            f"{name} must be ISO-8601."
        ) from exc


    if parsed.tzinfo is None:

        raise ValueError(
            f"{name} must include timezone."
        )


    return parsed


def _finite(
    value: Any,
    name: str,
) -> float:

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):

        raise ValueError(
            f"{name} must be numeric."
        )


    value = float(
        value
    )


    if not math.isfinite(
        value
    ):

        raise ValueError(
            f"{name} must be finite."
        )


    return value


def _risk_score(
    output: Mapping[
        str,
        Any,
    ],
) -> float | None:

    risk = output.get(
        "risk"
    )


    if not isinstance(
        risk,
        Mapping,
    ):

        return None


    score = risk.get(
        "stress_risk_score"
    )


    if score is None:

        return None


    score = _finite(
        score,
        "stress_risk_score",
    )


    if not (
        0.0 <= score <= 100.0
    ):

        raise ValueError(
            "stress_risk_score must be in [0, 100]."
        )


    return score


def _sensor_snapshot(
    output: Mapping[
        str,
        Any,
    ],
) -> Mapping[str, Any] | None:

    sensor = output.get(
        "sensor"
    )


    if not isinstance(
        sensor,
        Mapping,
    ):

        return None


    snapshot = sensor.get(
        "snapshot"
    )


    if not isinstance(
        snapshot,
        Mapping,
    ):

        return None


    return snapshot


def build_followup_plan(
    *,
    action_state: Mapping[
        str,
        Any,
    ],
    delay_seconds: Any,
    test_only: bool = False,
) -> dict[str, Any]:

    if not isinstance(
        action_state,
        Mapping,
    ):

        raise ValueError(
            "action_state must be a mapping."
        )


    if not isinstance(
        test_only,
        bool,
    ):

        raise ValueError(
            "test_only must be bool."
        )


    delay = _finite(
        delay_seconds,
        "delay_seconds",
    )


    if delay <= 0.0:

        raise ValueError(
            "delay_seconds must be > 0."
        )


    if (
        action_state.get(
            "action_state"
        )
        != "EXECUTED"
    ):

        return {
            "schema_version":
                FOLLOWUP_SCHEMA_VERSION,

            "status":
                "FOLLOWUP_NOT_SCHEDULED",

            "reason":
                "ACTION_NOT_EXECUTED",

            "command_id":
                action_state.get(
                    "command_id"
                ),

            "followup_due_at":
                None,

            "test_only":
                test_only,

            "real_intervention_verified":
                False,
        }


    state_time = _parse_timestamp(
        action_state.get(
            "state_timestamp"
        ),
        "state_timestamp",
    )


    if test_only:

        if (
            action_state.get(
                "simulated"
            )
            is not True
        ):

            raise ValueError(
                "test_only follow-up requires simulated action state."
            )


        verified = False


    else:

        if (
            action_state.get(
                "real_hardware_ack_validated"
            )
            is not True
            or action_state.get(
                "physical_actuation"
            )
            is not True
        ):

            return {
                "schema_version":
                    FOLLOWUP_SCHEMA_VERSION,

                "status":
                    "FOLLOWUP_BLOCKED",

                "reason":
                    "REAL_INTERVENTION_NOT_VERIFIED",

                "command_id":
                    action_state.get(
                        "command_id"
                    ),

                "followup_due_at":
                    None,

                "test_only":
                    False,

                "real_intervention_verified":
                    False,
            }


        verified = True


    due = (
        state_time
        + timedelta(
            seconds=delay
        )
    )


    return {
        "schema_version":
            FOLLOWUP_SCHEMA_VERSION,

        "status":
            (
                "SYNTHETIC_FOLLOWUP_PLANNED"
                if test_only
                else "FOLLOWUP_PLANNED"
            ),

        "command_id":
            action_state.get(
                "command_id"
            ),

        "plant_id":
            action_state.get(
                "plant_id"
            ),

        "action_state":
            "EXECUTED",

        "action_timestamp":
            state_time.isoformat(),

        "delay_seconds":
            delay,

        "followup_due_at":
            due.isoformat(),

        "test_only":
            test_only,

        "real_intervention_verified":
            verified,

        "scheduler_execution_performed":
            False,

        "physical_action_triggered":
            False,
    }


def analyze_closed_loop_outcome(
    *,
    action_state: Mapping[
        str,
        Any,
    ],
    before_output: Mapping[
        str,
        Any,
    ],
    after_output: Mapping[
        str,
        Any,
    ],
    test_only: bool = False,
) -> dict[str, Any]:

    if not all(
        isinstance(
            item,
            Mapping,
        )
        for item in (
            action_state,
            before_output,
            after_output,
        )
    ):

        raise ValueError(
            "action_state, before_output and after_output "
            "must be mappings."
        )


    if not isinstance(
        test_only,
        bool,
    ):

        raise ValueError(
            "test_only must be bool."
        )


    before_plant = before_output.get(
        "plant_id"
    )

    after_plant = after_output.get(
        "plant_id"
    )

    action_plant = action_state.get(
        "plant_id"
    )


    if not (
        isinstance(
            before_plant,
            str,
        )
        and before_plant
        == after_plant
        == action_plant
    ):

        raise ValueError(
            "Plant identity mismatch."
        )


    before_time = _parse_timestamp(
        before_output.get(
            "timestamp"
        ),
        "before timestamp",
    )

    after_time = _parse_timestamp(
        after_output.get(
            "timestamp"
        ),
        "after timestamp",
    )

    action_time = _parse_timestamp(
        action_state.get(
            "state_timestamp"
        ),
        "action timestamp",
    )


    if not (
        before_time
        <= action_time
        < after_time
    ):

        raise ValueError(
            "Invalid before/action/after chronology."
        )


    action_executed = (
        action_state.get(
            "action_state"
        )
        == "EXECUTED"
    )


    real_intervention_verified = (
        action_executed
        and action_state.get(
            "real_hardware_ack_validated"
        )
        is True
        and action_state.get(
            "physical_actuation"
        )
        is True
    )


    before_risk = _risk_score(
        before_output
    )

    after_risk = _risk_score(
        after_output
    )


    risk_delta = None


    if (
        before_risk is not None
        and after_risk is not None
    ):

        risk_delta = round(
            after_risk
            - before_risk,
            6,
        )


    before_sensor = _sensor_snapshot(
        before_output
    )

    after_sensor = _sensor_snapshot(
        after_output
    )


    sensor_response = {
        "soil_moisture_delta_pct_points":
            None,

        "temperature_delta_c":
            None,

        "humidity_delta_pct_points":
            None,
    }


    if (
        before_sensor is not None
        and after_sensor is not None
    ):

        pairs = [
            (
                "soil_moisture_pct",
                "soil_moisture_delta_pct_points",
            ),
            (
                "temperature_c",
                "temperature_delta_c",
            ),
            (
                "humidity_pct",
                "humidity_delta_pct_points",
            ),
        ]


        for source_key, output_key in pairs:

            before_value = (
                before_sensor.get(
                    source_key
                )
            )

            after_value = (
                after_sensor.get(
                    source_key
                )
            )


            if (
                before_value is not None
                and after_value is not None
            ):

                before_value = _finite(
                    before_value,
                    f"before {source_key}",
                )

                after_value = _finite(
                    after_value,
                    f"after {source_key}",
                )


                sensor_response[
                    output_key
                ] = round(
                    after_value
                    - before_value,
                    6,
                )


    risk_pair_available = (
        before_risk is not None
        and after_risk is not None
    )


    sensor_pair_available = (
        before_sensor is not None
        and after_sensor is not None
    )


    if test_only:

        outcome_status = (
            "SYNTHETIC_OBSERVED_CHANGE_ONLY"
        )

        validated_outcome = False


    elif not real_intervention_verified:

        outcome_status = (
            "INSUFFICIENT_INTERVENTION_EVIDENCE"
        )

        validated_outcome = False


    elif not risk_pair_available:

        outcome_status = (
            "INSUFFICIENT_RISK_EVIDENCE"
        )

        validated_outcome = False


    elif not sensor_pair_available:

        outcome_status = (
            "INSUFFICIENT_SENSOR_RESPONSE_EVIDENCE"
        )

        validated_outcome = False


    else:

        outcome_status = (
            "VALIDATED_OBSERVATIONAL_OUTCOME"
        )

        validated_outcome = True


    return {
        "schema_version":
            SCHEMA_VERSION,

        "command_id":
            action_state.get(
                "command_id"
            ),

        "plant_id":
            action_plant,

        "before_observation_id":
            before_output.get(
                "observation_id"
            ),

        "after_observation_id":
            after_output.get(
                "observation_id"
            ),

        "before_timestamp":
            before_time.isoformat(),

        "action_timestamp":
            action_time.isoformat(),

        "after_timestamp":
            after_time.isoformat(),

        "action_state":
            action_state.get(
                "action_state"
            ),

        "real_intervention_verified":
            real_intervention_verified,

        "risk": {
            "before":
                before_risk,

            "after":
                after_risk,

            "delta_after_minus_before":
                risk_delta,

            "pair_available":
                risk_pair_available,
        },

        "sensor_response":
            sensor_response,

        "sensor_pair_available":
            sensor_pair_available,

        "outcome_status":
            outcome_status,

        "validated_outcome":
            validated_outcome,

        "intervention_success_assumed":
            False,

        "causal_effect_claimed":
            False,

        "eligible_for_analytics":
            validated_outcome,

        "eligible_for_future_model_improvement":
            validated_outcome,

        "test_only":
            test_only,

        "scientific_guardrails": {
            "risk_decrease_means_irrigation_caused_recovery":
                False,

            "sensor_change_means_intervention_succeeded":
                False,

            "synthetic_change_is_real_outcome_evidence":
                False,

            "unverified_action_used_as_validated_outcome":
                False,
        },
    }
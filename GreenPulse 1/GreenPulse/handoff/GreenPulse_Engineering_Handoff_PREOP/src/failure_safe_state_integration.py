from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping, Optional

from src.failure_safe_state import (
    evaluate_failure_safe_state,
)


SCHEMA_VERSION = (
    "greenpulse.failure_safe_state_integration.v1"
)


def apply_failure_safe_state(
    system_output: Mapping[
        str,
        Any,
    ],
    failures: Iterable[
        Any
    ],
    *,
    config_path: Optional[Any] = None,
) -> dict[str, Any]:

    if not isinstance(
        system_output,
        Mapping,
    ):

        raise ValueError(
            "system_output must be a mapping."
        )


    original = deepcopy(
        dict(
            system_output
        )
    )


    safe_state = (
        evaluate_failure_safe_state(
            failures,
            config_path=config_path,
        )
    )


    effective_state = safe_state[
        "selected_safe_state"
    ]


    observation_id = (
        original.get(
            "observation_id"
        )
    )

    plant_id = (
        original.get(
            "plant_id"
        )
    )


    original_decision = deepcopy(
        original.get(
            "decision"
        )
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "source_schema_version":
            original.get(
                "schema_version"
            ),

        "observation_id":
            observation_id,

        "plant_id":
            plant_id,

        "failure_policy_version":
            safe_state[
                "policy_version"
            ],

        "failure_policy_status":
            safe_state[
                "policy_status"
            ],

        "failure_codes":
            list(
                safe_state[
                    "failure_codes"
                ]
            ),

        "reason_codes":
            list(
                safe_state[
                    "reason_codes"
                ]
            ),

        "effective_system_state":
            effective_state,

        "normal_decision_suppressed":
            True,

        "original_decision":
            original_decision,

        "safe_state": {
            "safe_mode":
                effective_state
                == "SAFE_MODE",

            "monitor":
                effective_state
                == "MONITOR",

            "manual_review":
                effective_state
                == "MANUAL_REVIEW",
        },

        "actuation_guard": {
            "hardware_dispatch_permitted_by_ai":
                False,

            "physical_actuation_authorized_by_ai":
                False,

            "direct_electrical_control":
                False,

            "blind_actuation_permitted":
                False,

            "normal_actuation_suppressed":
                True,
        },

        "execution": {
            "hardware_command_dispatched":
                False,

            "physical_actuation":
                False,

            "source_output_mutated":
                False,
        },

        "scientific_guardrails": {
            "safe_state_policy_operationally_validated":
                False,

            "real_failure_hardware_validation_claimed":
                False,

            "software_failure_injection_equals_real_failure":
                False,
        },
    }
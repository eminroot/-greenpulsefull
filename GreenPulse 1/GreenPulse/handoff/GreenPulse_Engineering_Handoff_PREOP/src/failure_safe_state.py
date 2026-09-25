from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import json


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONFIG = (
    ROOT
    / "configs"
    / "failure_safe_state_v1.json"
)

POLICY_SCHEMA_VERSION = (
    "greenpulse.failure_safe_state_policy.v1"
)

RESULT_SCHEMA_VERSION = (
    "greenpulse.failure_safe_state_result.v1"
)


REQUIRED_FAILURES = (
    "CAMERA_MISSING",
    "CAMERA_TIMEOUT",
    "BLURRED_IMAGE",
    "SENSOR_MISSING",
    "SENSOR_INVALID",
    "SENSOR_STALE",
    "WIFI_FAILURE",
    "LOW_CONFIDENCE",
    "VISION_SENSOR_CONFLICT",
    "DB_FAILURE",
    "HARDWARE_TIMEOUT",
)


def load_failure_policy(
    config_path: Optional[Any] = None,
) -> dict[str, Any]:

    path = (
        Path(
            config_path
        )
        if config_path is not None
        else DEFAULT_CONFIG
    )


    policy = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


    validate_failure_policy(
        policy
    )


    return policy


def validate_failure_policy(
    policy: Mapping[
        str,
        Any,
    ],
) -> None:

    if not isinstance(
        policy,
        Mapping,
    ):

        raise ValueError(
            "Failure policy must be a mapping."
        )


    if (
        policy.get(
            "schema_version"
        )
        != POLICY_SCHEMA_VERSION
    ):

        raise ValueError(
            "Unsupported failure policy schema."
        )


    if (
        policy.get(
            "policy_status"
        )
        != "DEVELOPMENT_ONLY_UNVALIDATED"
    ):

        raise ValueError(
            "Failure policy must remain development-only."
        )


    allowed = policy.get(
        "allowed_safe_states"
    )

    priority = policy.get(
        "state_priority"
    )

    mapping = policy.get(
        "failure_mapping"
    )

    actuation = policy.get(
        "actuation_policy"
    )


    if not isinstance(
        allowed,
        list,
    ):

        raise ValueError(
            "allowed_safe_states missing."
        )


    if set(
        allowed
    ) != {
        "SAFE_MODE",
        "MONITOR",
        "MANUAL_REVIEW",
    }:

        raise ValueError(
            "Unexpected allowed safe states."
        )


    if (
        not isinstance(
            priority,
            list,
        )
        or set(
            priority
        )
        != set(
            allowed
        )
    ):

        raise ValueError(
            "state_priority invalid."
        )


    if not isinstance(
        mapping,
        Mapping,
    ):

        raise ValueError(
            "failure_mapping missing."
        )


    for failure in REQUIRED_FAILURES:

        state = mapping.get(
            failure
        )


        if state not in allowed:

            raise ValueError(
                f"Invalid mapping for {failure}."
            )


    if not isinstance(
        actuation,
        Mapping,
    ):

        raise ValueError(
            "actuation_policy missing."
        )


    for field in (
        "hardware_dispatch_permitted",
        "physical_actuation_authorized",
        "direct_electrical_control",
        "blind_actuation_permitted",
    ):

        if (
            actuation.get(
                field
            )
            is not False
        ):

            raise ValueError(
                f"{field} must remain false."
            )


def _normalize_failure(
    value: Any,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):

        raise ValueError(
            "Failure code must be a non-empty string."
        )


    normalized = (
        value.strip()
        .upper()
        .replace(
            "-",
            "_",
        )
        .replace(
            " ",
            "_",
        )
    )


    if normalized not in REQUIRED_FAILURES:

        raise ValueError(
            f"Unsupported failure code: {normalized}"
        )


    return normalized


def evaluate_failure_safe_state(
    failures: Iterable[
        Any
    ],
    *,
    config_path: Optional[Any] = None,
) -> dict[str, Any]:

    if isinstance(
        failures,
        (str, bytes),
    ):

        raise ValueError(
            "failures must be an iterable of failure codes."
        )


    normalized = []


    for failure in failures:

        code = _normalize_failure(
            failure
        )


        if code not in normalized:

            normalized.append(
                code
            )


    if not normalized:

        raise ValueError(
            "At least one failure code is required."
        )


    policy = load_failure_policy(
        config_path
    )


    mapping = policy[
        "failure_mapping"
    ]

    priority = {
        state:
            index

        for index, state
        in enumerate(
            policy[
                "state_priority"
            ]
        )
    }


    mapped_states = [
        mapping[
            failure
        ]
        for failure in normalized
    ]


    selected_state = max(
        mapped_states,
        key=lambda state:
            priority[
                state
            ],
    )


    reason_codes = [
        "FAILURE_"
        + failure
        for failure in normalized
    ]


    return {
        "schema_version":
            RESULT_SCHEMA_VERSION,

        "policy_schema_version":
            POLICY_SCHEMA_VERSION,

        "policy_version":
            policy[
                "policy_version"
            ],

        "policy_status":
            policy[
                "policy_status"
            ],

        "failure_codes":
            normalized,

        "mapped_states":
            {
                failure:
                    mapping[
                        failure
                    ]

                for failure
                in normalized
            },

        "selected_safe_state":
            selected_state,

        "reason_codes":
            reason_codes,

        "system_behavior": {
            "degraded":
                True,

            "crash_requested":
                False,

            "continue_normal_actuation":
                False,

            "safe_mode":
                selected_state
                == "SAFE_MODE",

            "monitor":
                selected_state
                == "MONITOR",

            "manual_review":
                selected_state
                == "MANUAL_REVIEW",
        },

        "actuation_guard": {
            "hardware_dispatch_permitted":
                False,

            "physical_actuation_authorized":
                False,

            "direct_electrical_control":
                False,

            "blind_actuation_permitted":
                False,
        },

        "scientific_guardrails": {
            "policy_operationally_validated":
                False,

            "failure_mapping_claimed_optimal":
                False,

            "real_hardware_validation_claimed":
                False,
        },
    }
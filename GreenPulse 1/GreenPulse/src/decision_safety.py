from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

import json
import math


SCHEMA_VERSION = (
    "greenpulse.decision_safety.v1"
)

POLICY_SCHEMA_VERSION = (
    "greenpulse.safety_policy.v1"
)

DEFAULT_POLICY = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "safety_policy.yaml"
)


VALID_POLICY_STATUSES = {
    "DEVELOPMENT_ONLY_UNVALIDATED",
    "SYNTHETIC_TEST_ONLY",
    "OPERATIONAL_VALIDATED",
}


VALID_MANUAL_OVERRIDE_MODES = {
    "NONE",
    "FORCE_BLOCK",
    "MANUAL_REVIEW",
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


def _finite_number(
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

    return result


def _optional_nonnegative(
    value: Any,
    name: str,
) -> Optional[float]:

    if value is None:
        return None

    result = _finite_number(
        value,
        name,
    )

    if result < 0.0:

        raise ValueError(
            f"{name} must be >= 0."
        )

    return result


def _validate_policy(
    policy: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        policy,
        Mapping,
    ):

        raise ValueError(
            "Safety policy must be a mapping."
        )


    if (
        policy.get(
            "schema_version"
        )
        != POLICY_SCHEMA_VERSION
    ):

        raise ValueError(
            "Unsupported safety-policy schema."
        )


    policy_version = policy.get(
        "policy_version"
    )

    if (
        not isinstance(
            policy_version,
            str,
        )
        or not policy_version.strip()
    ):

        raise ValueError(
            "policy_version is required."
        )


    policy_status = policy.get(
        "policy_status"
    )

    if policy_status not in VALID_POLICY_STATUSES:

        raise ValueError(
            "Unsupported policy_status."
        )


    autonomous_enabled = _strict_bool(
        policy.get(
            "autonomous_request_enabled"
        ),
        "autonomous_request_enabled",
    )


    minimum_confidence = (
        _optional_nonnegative(
            policy.get(
                "minimum_confidence"
            ),
            "minimum_confidence",
        )
    )


    if (
        minimum_confidence
        is not None
        and minimum_confidence > 1.0
    ):

        raise ValueError(
            "minimum_confidence must be in [0, 1]."
        )


    minimum_risk = _optional_nonnegative(
        policy.get(
            "minimum_risk_score"
        ),
        "minimum_risk_score",
    )


    if (
        minimum_risk
        is not None
        and minimum_risk > 100.0
    ):

        raise ValueError(
            "minimum_risk_score must be in [0, 100]."
        )


    confirmation_count = policy.get(
        "confirmation_count"
    )


    if confirmation_count is not None:

        if (
            isinstance(
                confirmation_count,
                bool,
            )
            or not isinstance(
                confirmation_count,
                int,
            )
            or confirmation_count < 1
        ):

            raise ValueError(
                "confirmation_count must be "
                "an integer >= 1."
            )


    cooldown_seconds = (
        _optional_nonnegative(
            policy.get(
                "cooldown_seconds"
            ),
            "cooldown_seconds",
        )
    )


    maximum_duration = (
        _optional_nonnegative(
            policy.get(
                "maximum_requested_action_duration_seconds"
            ),
            "maximum_requested_action_duration_seconds",
        )
    )


    if (
        maximum_duration is not None
        and maximum_duration <= 0.0
    ):

        raise ValueError(
            "maximum requested action duration "
            "must be > 0."
        )


    require_camera_valid = (
        _strict_bool(
            policy.get(
                "require_camera_valid"
            ),
            "require_camera_valid",
        )
    )


    require_sensor_valid = (
        _strict_bool(
            policy.get(
                "require_sensor_valid"
            ),
            "require_sensor_valid",
        )
    )


    manual = policy.get(
        "manual_override"
    )


    if not isinstance(
        manual,
        Mapping,
    ):

        raise ValueError(
            "manual_override configuration missing."
        )


    manual_enabled = _strict_bool(
        manual.get(
            "enabled"
        ),
        "manual_override.enabled",
    )


    allowed_modes = manual.get(
        "allowed_modes"
    )


    if (
        not isinstance(
            allowed_modes,
            list,
        )
        or not allowed_modes
    ):

        raise ValueError(
            "manual_override.allowed_modes invalid."
        )


    if not set(
        allowed_modes
    ).issubset(
        VALID_MANUAL_OVERRIDE_MODES
    ):

        raise ValueError(
            "Unsupported manual override mode."
        )


    physical_bypass = _strict_bool(
        manual.get(
            "physical_safety_bypass_allowed"
        ),
        "manual_override.physical_safety_bypass_allowed",
    )


    if physical_bypass:

        raise ValueError(
            "Physical safety bypass is forbidden."
        )


    if policy_status in {
        "SYNTHETIC_TEST_ONLY",
        "OPERATIONAL_VALIDATED",
    }:

        required_numeric = {
            "minimum_confidence":
                minimum_confidence,

            "minimum_risk_score":
                minimum_risk,

            "confirmation_count":
                confirmation_count,

            "cooldown_seconds":
                cooldown_seconds,

            "maximum_requested_action_duration_seconds":
                maximum_duration,
        }


        missing = [
            name
            for name, value
            in required_numeric.items()
            if value is None
        ]


        if missing:

            raise ValueError(
                "Validated/test policy is missing "
                "required constraints: "
                + ", ".join(
                    missing
                )
            )


    return {
        "schema_version":
            POLICY_SCHEMA_VERSION,

        "policy_version":
            policy_version.strip(),

        "policy_status":
            policy_status,

        "autonomous_request_enabled":
            autonomous_enabled,

        "minimum_confidence":
            minimum_confidence,

        "minimum_risk_score":
            minimum_risk,

        "confirmation_count":
            confirmation_count,

        "cooldown_seconds":
            cooldown_seconds,

        "maximum_requested_action_duration_seconds":
            maximum_duration,

        "require_camera_valid":
            require_camera_valid,

        "require_sensor_valid":
            require_sensor_valid,

        "manual_override": {
            "enabled":
                manual_enabled,

            "allowed_modes":
                list(
                    allowed_modes
                ),

            "physical_safety_bypass_allowed":
                False,
        },
    }


def load_safety_policy(
    path: Path = DEFAULT_POLICY,
) -> dict[str, Any]:

    path = Path(
        path
    )


    if not path.is_file():

        raise FileNotFoundError(
            path
        )


    try:

        # JSON syntax is a valid YAML 1.2 subset.
        # This avoids adding an external YAML parser
        # merely to load this conservative policy.
        payload = json.loads(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            "safety_policy.yaml must use the "
            "supported YAML-1.2 JSON subset."
        ) from exc


    return _validate_policy(
        payload
    )


def _normalize_context(
    context: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        context,
        Mapping,
    ):

        raise ValueError(
            "safety_context must be a mapping."
        )


    confidence = context.get(
        "model_confidence"
    )


    if confidence is not None:

        confidence = _finite_number(
            confidence,
            "model_confidence",
        )

        if not (
            0.0
            <= confidence
            <= 1.0
        ):

            raise ValueError(
                "model_confidence must be in [0, 1]."
            )


    risk = context.get(
        "stress_risk_score"
    )


    if risk is not None:

        risk = _finite_number(
            risk,
            "stress_risk_score",
        )

        if not (
            0.0
            <= risk
            <= 100.0
        ):

            raise ValueError(
                "stress_risk_score must be in [0, 100]."
            )


    confirmation_count = context.get(
        "confirmation_count"
    )


    if confirmation_count is not None:

        if (
            isinstance(
                confirmation_count,
                bool,
            )
            or not isinstance(
                confirmation_count,
                int,
            )
            or confirmation_count < 0
        ):

            raise ValueError(
                "confirmation_count must be integer >= 0."
            )


    cooldown = context.get(
        "seconds_since_last_request"
    )


    if cooldown is not None:

        cooldown = _finite_number(
            cooldown,
            "seconds_since_last_request",
        )

        if cooldown < 0.0:

            raise ValueError(
                "seconds_since_last_request must be >= 0."
            )


    requested_duration = context.get(
        "requested_action_duration_seconds"
    )


    if requested_duration is not None:

        requested_duration = _finite_number(
            requested_duration,
            "requested_action_duration_seconds",
        )

        if requested_duration <= 0.0:

            raise ValueError(
                "requested action duration must be > 0."
            )


    camera_valid = _strict_bool(
        context.get(
            "camera_valid"
        ),
        "camera_valid",
    )


    sensor_valid = _strict_bool(
        context.get(
            "sensor_valid"
        ),
        "sensor_valid",
    )


    manual_override = context.get(
        "manual_override",
        "NONE",
    )


    if manual_override not in VALID_MANUAL_OVERRIDE_MODES:

        raise ValueError(
            "Unsupported manual_override."
        )


    return {
        "model_confidence":
            confidence,

        "stress_risk_score":
            risk,

        "confirmation_count":
            confirmation_count,

        "seconds_since_last_request":
            cooldown,

        "requested_action_duration_seconds":
            requested_duration,

        "camera_valid":
            camera_valid,

        "sensor_valid":
            sensor_valid,

        "manual_override":
            manual_override,
    }


def _evaluate_constraints(
    *,
    policy: Mapping[
        str,
        Any,
    ],
    context: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    reasons = []

    checks = {}


    confidence = context[
        "model_confidence"
    ]

    confidence_pass = (
        confidence is not None
        and confidence
        >= policy[
            "minimum_confidence"
        ]
    )

    checks[
        "minimum_confidence"
    ] = confidence_pass

    if not confidence_pass:

        reasons.append(
            "MINIMUM_CONFIDENCE_NOT_MET"
        )


    risk = context[
        "stress_risk_score"
    ]

    risk_pass = (
        risk is not None
        and risk
        >= policy[
            "minimum_risk_score"
        ]
    )

    checks[
        "minimum_risk"
    ] = risk_pass

    if not risk_pass:

        reasons.append(
            "MINIMUM_RISK_NOT_MET"
        )


    confirmation = context[
        "confirmation_count"
    ]

    confirmation_pass = (
        confirmation is not None
        and confirmation
        >= policy[
            "confirmation_count"
        ]
    )

    checks[
        "confirmation_count"
    ] = confirmation_pass

    if not confirmation_pass:

        reasons.append(
            "CONFIRMATION_COUNT_NOT_MET"
        )


    cooldown = context[
        "seconds_since_last_request"
    ]

    cooldown_pass = (
        cooldown is None
        or cooldown
        >= policy[
            "cooldown_seconds"
        ]
    )

    checks[
        "cooldown"
    ] = cooldown_pass

    if not cooldown_pass:

        reasons.append(
            "COOLDOWN_ACTIVE"
        )


    duration = context[
        "requested_action_duration_seconds"
    ]

    duration_pass = (
        duration is not None
        and duration
        <= policy[
            "maximum_requested_action_duration_seconds"
        ]
    )

    checks[
        "maximum_requested_action_duration"
    ] = duration_pass

    if not duration_pass:

        reasons.append(
            "REQUESTED_ACTION_DURATION_EXCEEDS_LIMIT"
        )


    camera_pass = (
        not policy[
            "require_camera_valid"
        ]
        or context[
            "camera_valid"
        ]
    )

    checks[
        "camera_validity"
    ] = camera_pass

    if not camera_pass:

        reasons.append(
            "CAMERA_INVALID"
        )


    sensor_pass = (
        not policy[
            "require_sensor_valid"
        ]
        or context[
            "sensor_valid"
        ]
    )

    checks[
        "sensor_validity"
    ] = sensor_pass

    if not sensor_pass:

        reasons.append(
            "SENSOR_INVALID"
        )


    return {
        "checks":
            checks,

        "passed":
            all(
                checks.values()
            ),

        "reason_codes":
            reasons,
    }


def evaluate_decision_safety(
    *,
    decision_result: Mapping[
        str,
        Any,
    ],
    safety_context: Mapping[
        str,
        Any,
    ],
    policy: Optional[
        Mapping[str, Any]
    ] = None,
    policy_path: Path = DEFAULT_POLICY,
    test_only: bool = False,
) -> dict[str, Any]:

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


    if not isinstance(
        decision,
        str,
    ):

        raise ValueError(
            "decision_result.decision is required."
        )


    test_only = _strict_bool(
        test_only,
        "test_only",
    )


    if policy is None:

        normalized_policy = (
            load_safety_policy(
                policy_path
            )
        )

    else:

        normalized_policy = (
            _validate_policy(
                policy
            )
        )


    context = _normalize_context(
        safety_context
    )


    manual = context[
        "manual_override"
    ]


    base = {
        "schema_version":
            SCHEMA_VERSION,

        "policy_version":
            normalized_policy[
                "policy_version"
            ],

        "policy_status":
            normalized_policy[
                "policy_status"
            ],

        "input_decision":
            decision,

        "manual_override":
            manual,

        "request_allowed_by_safety_policy":
            False,

        "hardware_safety_checks_required":
            True,

        "hardware_dispatch_permitted":
            False,

        "physical_actuation_authorized":
            False,

        "actuator_command":
            None,
    }


    if (
        manual
        != "NONE"
        and not normalized_policy[
            "manual_override"
        ][
            "enabled"
        ]
    ):

        return {
            **base,

            "status":
                "BLOCKED_MANUAL_OVERRIDE_DISABLED",

            "routing":
                "RECHECK",

            "constraint_checks":
                None,

            "reason_codes": [
                "MANUAL_OVERRIDE_DISABLED"
            ],
        }


    if manual == "FORCE_BLOCK":

        return {
            **base,

            "status":
                "BLOCKED_MANUAL_OVERRIDE",

            "routing":
                "NO_ACTION",

            "constraint_checks":
                None,

            "reason_codes": [
                "MANUAL_FORCE_BLOCK"
            ],
        }


    if manual == "MANUAL_REVIEW":

        return {
            **base,

            "status":
                "MANUAL_REVIEW_REQUIRED",

            "routing":
                "MANUAL_REVIEW",

            "constraint_checks":
                None,

            "reason_codes": [
                "MANUAL_REVIEW_OVERRIDE"
            ],
        }


    if decision != "IRRIGATION_REQUEST":

        return {
            **base,

            "status":
                "NO_IRRIGATION_REQUEST_TO_EVALUATE",

            "routing":
                decision,

            "constraint_checks":
                None,

            "reason_codes": [
                "NO_IRRIGATION_REQUEST"
            ],
        }


    policy_status = normalized_policy[
        "policy_status"
    ]


    if (
        policy_status
        == "DEVELOPMENT_ONLY_UNVALIDATED"
    ):

        return {
            **base,

            "status":
                "BLOCKED_POLICY_NOT_OPERATIONALLY_VALIDATED",

            "routing":
                "WARNING",

            "constraint_checks":
                None,

            "reason_codes": [
                "SAFETY_POLICY_NOT_OPERATIONALLY_VALIDATED",
                "OPERATIONAL_THRESHOLDS_UNAVAILABLE",
            ],
        }


    constraint_result = (
        _evaluate_constraints(
            policy=
                normalized_policy,

            context=
                context,
        )
    )


    if not constraint_result[
        "passed"
    ]:

        return {
            **base,

            "status":
                "BLOCKED_SAFETY_CONSTRAINT",

            "routing":
                "RECHECK",

            "constraint_checks":
                constraint_result[
                    "checks"
                ],

            "reason_codes":
                constraint_result[
                    "reason_codes"
                ],
        }


    if (
        policy_status
        == "SYNTHETIC_TEST_ONLY"
    ):

        if not test_only:

            return {
                **base,

                "status":
                    "BLOCKED_SYNTHETIC_POLICY_OUTSIDE_TEST_MODE",

                "routing":
                    "RECHECK",

                "constraint_checks":
                    constraint_result[
                        "checks"
                    ],

                "reason_codes": [
                    "SYNTHETIC_POLICY_TEST_MODE_REQUIRED"
                ],
            }


        return {
            **base,

            "status":
                "SYNTHETIC_POLICY_LOGIC_PASS",

            "routing":
                "TEST_ONLY",

            "constraint_checks":
                constraint_result[
                    "checks"
                ],

            "reason_codes": [
                "SYNTHETIC_SAFETY_CONSTRAINTS_PASSED"
            ],

            "request_allowed_by_safety_policy":
                False,
        }


    if (
        policy_status
        != "OPERATIONAL_VALIDATED"
    ):

        raise RuntimeError(
            "Unexpected policy state."
        )


    if not normalized_policy[
        "autonomous_request_enabled"
    ]:

        return {
            **base,

            "status":
                "BLOCKED_AUTONOMOUS_REQUEST_DISABLED",

            "routing":
                "WARNING",

            "constraint_checks":
                constraint_result[
                    "checks"
                ],

            "reason_codes": [
                "AUTONOMOUS_REQUEST_DISABLED"
            ],
        }


    # This means only that Layer 33 policy logic
    # allows the request to PROCEED TO the hardware
    # controller's electrical/physical safety checks.
    #
    # It is still not hardware dispatch or actuation.
    return {
        **base,

        "status":
            "REQUEST_ELIGIBLE_FOR_HARDWARE_SAFETY_CHECKS",

        "routing":
            "HARDWARE_SAFETY_CHECK",

        "constraint_checks":
            constraint_result[
                "checks"
            ],

        "reason_codes": [
            "DECISION_SAFETY_POLICY_PASSED"
        ],

        "request_allowed_by_safety_policy":
            True,

        "hardware_dispatch_permitted":
            False,

        "physical_actuation_authorized":
            False,

        "actuator_command":
            None,
    }
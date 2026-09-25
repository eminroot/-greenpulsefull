from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Optional

import json
import math
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONFIG = (
    ROOT
    / "configs"
    / "adaptive_sampling_v1.json"
)

POLICY_SCHEMA_VERSION = (
    "greenpulse.adaptive_sampling_policy.v1"
)

DECISION_SCHEMA_VERSION = (
    "greenpulse.adaptive_sampling_decision.v1"
)


def _finite_optional_score(
    value: Any,
    name: str,
) -> Optional[float]:

    if value is None:

        return None


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
            f"{name} must be numeric or null."
        )


    parsed = float(
        value
    )


    if (
        not math.isfinite(
            parsed
        )
        or not 0.0
        <= parsed
        <= 100.0
    ):

        raise ValueError(
            f"{name} must be in [0, 100]."
        )


    return parsed


def _timestamp(
    value: Any,
) -> datetime:

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):

        raise ValueError(
            "timestamp is required."
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
            "timestamp must be ISO-8601."
        ) from exc


    if parsed.tzinfo is None:

        raise ValueError(
            "timestamp must include timezone."
        )


    return parsed


def load_sampling_policy(
    config_path: Optional[Any] = None,
) -> dict[str, Any]:

    path = (
        Path(
            config_path
        )
        if config_path
        is not None
        else DEFAULT_CONFIG
    )


    policy = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


    validate_sampling_policy(
        policy
    )


    return policy


def validate_sampling_policy(
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
            "Sampling policy must be a mapping."
        )


    if (
        policy.get(
            "schema_version"
        )
        != POLICY_SCHEMA_VERSION
    ):

        raise ValueError(
            "Unsupported sampling policy schema."
        )


    if (
        policy.get(
            "policy_status"
        )
        != "DEVELOPMENT_ONLY_UNVALIDATED"
    ):

        raise ValueError(
            "Sampling policy must remain development-only "
            "until operational validation exists."
        )


    intervals = policy.get(
        "intervals_seconds"
    )

    risk = policy.get(
        "risk_thresholds"
    )

    forecast = policy.get(
        "forecast_thresholds"
    )

    trends = policy.get(
        "trend_states"
    )


    if not all(
        isinstance(
            item,
            Mapping,
        )
        for item in (
            intervals,
            risk,
            forecast,
            trends,
        )
    ):

        raise ValueError(
            "Sampling policy sections missing."
        )


    required_intervals = (
        "stable_healthy",
        "normal",
        "elevated",
        "high",
    )


    for name in required_intervals:

        value = intervals.get(
            name
        )


        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                (int, float),
            )
            or float(
                value
            )
            <= 0
        ):

            raise ValueError(
                f"Invalid interval: {name}"
            )


    if not (
        float(
            intervals[
                "stable_healthy"
            ]
        )
        >
        float(
            intervals[
                "normal"
            ]
        )
        >
        float(
            intervals[
                "elevated"
            ]
        )
        >
        float(
            intervals[
                "high"
            ]
        )
    ):

        raise ValueError(
            "Sampling intervals must become shorter "
            "as urgency rises."
        )


    for section_name, section in (
        (
            "risk_thresholds",
            risk,
        ),
        (
            "forecast_thresholds",
            forecast,
        ),
    ):

        elevated = _finite_optional_score(
            section.get(
                "elevated"
            ),
            f"{section_name}.elevated",
        )

        high = _finite_optional_score(
            section.get(
                "high"
            ),
            f"{section_name}.high",
        )


        if (
            elevated is None
            or high is None
            or elevated >= high
        ):

            raise ValueError(
                f"Invalid thresholds in {section_name}."
            )


    for key in (
        "stable",
        "rising",
        "rapid_rise",
    ):

        values = trends.get(
            key
        )


        if (
            not isinstance(
                values,
                list,
            )
            or not values
            or not all(
                isinstance(
                    value,
                    str,
                )
                and value.strip()
                for value in values
            )
        ):

            raise ValueError(
                f"Invalid trend state group: {key}"
            )


def evaluate_adaptive_sampling(
    context: Mapping[
        str,
        Any,
    ],
    *,
    config_path: Optional[Any] = None,
) -> dict[str, Any]:

    if not isinstance(
        context,
        Mapping,
    ):

        raise ValueError(
            "context must be a mapping."
        )


    plant_id = context.get(
        "plant_id"
    )

    observation_id = context.get(
        "observation_id"
    )


    if (
        not isinstance(
            plant_id,
            str,
        )
        or not plant_id.strip()
    ):

        raise ValueError(
            "plant_id is required."
        )


    if (
        not isinstance(
            observation_id,
            str,
        )
        or not observation_id.strip()
    ):

        raise ValueError(
            "observation_id is required."
        )


    observed_at = _timestamp(
        context.get(
            "timestamp"
        )
    )


    stable_healthy_confirmed = context.get(
        "stable_healthy_confirmed",
        False,
    )


    if not isinstance(
        stable_healthy_confirmed,
        bool,
    ):

        raise ValueError(
            "stable_healthy_confirmed must be bool."
        )


    risk_score = _finite_optional_score(
        context.get(
            "risk_score"
        ),
        "risk_score",
    )

    forecast_score = _finite_optional_score(
        context.get(
            "forecast_risk_score"
        ),
        "forecast_risk_score",
    )


    trend_state = context.get(
        "trend_state"
    )


    if trend_state is not None:

        if not isinstance(
            trend_state,
            str,
        ):

            raise ValueError(
                "trend_state must be string or null."
            )

        trend_state = (
            trend_state.strip().upper()
        )


    policy = load_sampling_policy(
        config_path
    )


    intervals = policy[
        "intervals_seconds"
    ]

    risk_thresholds = policy[
        "risk_thresholds"
    ]

    forecast_thresholds = policy[
        "forecast_thresholds"
    ]

    trend_groups = policy[
        "trend_states"
    ]


    stable_states = {
        value.upper()
        for value
        in trend_groups[
            "stable"
        ]
    }

    rising_states = {
        value.upper()
        for value
        in trend_groups[
            "rising"
        ]
    }

    rapid_states = {
        value.upper()
        for value
        in trend_groups[
            "rapid_rise"
        ]
    }


    level = "normal"

    reason_codes = []


    high_signal = (
        (
            risk_score
            is not None
            and risk_score
            >= float(
                risk_thresholds[
                    "high"
                ]
            )
        )
        or (
            forecast_score
            is not None
            and forecast_score
            >= float(
                forecast_thresholds[
                    "high"
                ]
            )
        )
        or (
            trend_state
            in rapid_states
        )
    )


    elevated_signal = (
        (
            risk_score
            is not None
            and risk_score
            >= float(
                risk_thresholds[
                    "elevated"
                ]
            )
        )
        or (
            forecast_score
            is not None
            and forecast_score
            >= float(
                forecast_thresholds[
                    "elevated"
                ]
            )
        )
        or (
            trend_state
            in rising_states
        )
    )


    if high_signal:

        level = "high"

        if (
            risk_score
            is not None
            and risk_score
            >= float(
                risk_thresholds[
                    "high"
                ]
            )
        ):

            reason_codes.append(
                "HIGH_CURRENT_RISK"
            )


        if (
            forecast_score
            is not None
            and forecast_score
            >= float(
                forecast_thresholds[
                    "high"
                ]
            )
        ):

            reason_codes.append(
                "HIGH_FORECAST_RISK"
            )


        if trend_state in rapid_states:

            reason_codes.append(
                "RAPID_RISK_RISE"
            )


    elif elevated_signal:

        level = "elevated"


        if (
            risk_score
            is not None
            and risk_score
            >= float(
                risk_thresholds[
                    "elevated"
                ]
            )
        ):

            reason_codes.append(
                "ELEVATED_CURRENT_RISK"
            )


        if (
            forecast_score
            is not None
            and forecast_score
            >= float(
                forecast_thresholds[
                    "elevated"
                ]
            )
        ):

            reason_codes.append(
                "ELEVATED_FORECAST_RISK"
            )


        if trend_state in rising_states:

            reason_codes.append(
                "RISING_RISK_TREND"
            )


    elif stable_healthy_confirmed:

        if (
            trend_state is None
            or trend_state in stable_states
        ):

            level = "stable_healthy"

            reason_codes.append(
                "VALIDATED_STABLE_HEALTHY_STATE"
            )

        else:

            reason_codes.append(
                "STABLE_HEALTHY_CONFLICT_WITH_TREND"
            )


    else:

        reason_codes.append(
            "NORMAL_OBSERVATION_CADENCE"
        )


    if (
        trend_state is not None
        and trend_state
        not in stable_states
        and trend_state
        not in rising_states
        and trend_state
        not in rapid_states
    ):

        reason_codes.append(
            "UNKNOWN_TREND_STATE"
        )


    interval = float(
        intervals[
            level
        ]
    )


    next_observation = (
        observed_at
        + timedelta(
            seconds=interval
        )
    )


    decision_id = str(
        uuid4()
    )


    return {
        "schema_version":
            DECISION_SCHEMA_VERSION,

        "decision_id":
            decision_id,

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

        "plant_id":
            plant_id,

        "observation_id":
            observation_id,

        "observation_timestamp":
            observed_at.isoformat(),

        "sampling_level":
            level.upper(),

        "interval_seconds":
            interval,

        "next_observation_at":
            next_observation.isoformat(),

        "reason_codes":
            reason_codes,

        "input_summary": {
            "risk_score":
                risk_score,

            "forecast_risk_score":
                forecast_score,

            "trend_state":
                trend_state,

            "stable_healthy_confirmed":
                stable_healthy_confirmed,
        },

        "audit_record": {
            "decision_id":
                decision_id,

            "policy_version":
                policy[
                    "policy_version"
                ],

            "sampling_level":
                level.upper(),

            "interval_seconds":
                interval,

            "reason_codes":
                list(
                    reason_codes
                ),
        },

        "scientific_guardrails": {
            "disease_healthy_label_alone_reduces_frequency":
                False,

            "energy_savings_claimed":
                False,

            "cpu_savings_claimed":
                False,

            "storage_savings_claimed":
                False,

            "network_savings_claimed":
                False,

            "response_quality_preservation_validated":
                False,

            "policy_thresholds_operationally_validated":
                False,
        },
    }
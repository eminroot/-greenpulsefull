from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

import math


SCHEMA_VERSION = (
    "greenpulse.temporal_intelligence.v1"
)

FEATURE_VECTOR_VERSION = (
    "temporal_feature_vector_v1"
)

EXPECTED_RISK_CALIBRATION_SCHEMA = (
    "greenpulse.risk_calibration.v1"
)

FEATURE_VECTOR_NAMES = [
    "risk_trend_code",
    "risk_velocity",
    "risk_acceleration",
    "temporal_consistency_code",
]


TREND_TO_CODE = {
    "FALLING":
        -1.0,

    "STABLE":
        0.0,

    "RISING":
        1.0,
}


CONSISTENCY_TO_CODE = {
    "RECHECK":
        0.0,

    "CONFIRMED_STRESS":
        1.0,
}


SENSOR_FIELDS = [
    "soil_moisture_pct",
    "temperature_c",
    "humidity_pct",
]


def _finite_float(
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


def _parse_timestamp(
    value: Any,
) -> datetime:

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "timestamp must be an ISO-8601 string."
        )

    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:

        raise ValueError(
            "Invalid timestamp."
        ) from exc

    if parsed.tzinfo is None:

        raise ValueError(
            "Timestamp timezone is required."
        )

    return parsed.astimezone(
        timezone.utc
    )


def _validate_score(
    value: Any,
) -> float:

    score = _finite_float(
        value,
        "stress_risk_score",
    )

    if not (
        0.0
        <= score
        <= 100.0
    ):
        raise ValueError(
            "stress_risk_score must be in [0, 100]."
        )

    return score


def _extract_sensor_values(
    observation: Mapping[
        str,
        Any,
    ],
) -> dict[str, Optional[float]]:

    direct = observation.get(
        "sensor_values"
    )

    if isinstance(
        direct,
        Mapping,
    ):

        result = {}

        for field in SENSOR_FIELDS:

            value = direct.get(
                field
            )

            result[
                field
            ] = (
                None
                if value is None
                else _finite_float(
                    value,
                    field,
                )
            )

        return result


    sensor_features = observation.get(
        "sensor_features"
    )

    if not isinstance(
        sensor_features,
        Mapping,
    ):

        return {
            field:
                None
            for field in SENSOR_FIELDS
        }


    if (
        sensor_features.get(
            "feature_vector_version"
        )
        != "sensor_feature_vector_v1"
    ):

        raise ValueError(
            "Unsupported sensor feature-vector version."
        )


    vector = sensor_features.get(
        "feature_vector"
    )

    if not isinstance(
        vector,
        Mapping,
    ):

        raise ValueError(
            "Sensor feature_vector missing."
        )


    names = vector.get(
        "names"
    )

    values = vector.get(
        "raw_values"
    )

    if not isinstance(
        names,
        list,
    ) or not isinstance(
        values,
        list,
    ):

        raise ValueError(
            "Sensor names/raw_values missing."
        )


    if len(
        names
    ) != len(
        values
    ):

        raise ValueError(
            "Sensor name/value length mismatch."
        )


    mapping = dict(
        zip(
            names,
            values,
        )
    )


    result = {}

    for field in SENSOR_FIELDS:

        value = mapping.get(
            field
        )

        result[
            field
        ] = (
            None
            if value is None
            else _finite_float(
                value,
                field,
            )
        )

    return result


def _validate_observation(
    observation: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        observation,
        Mapping,
    ):

        raise TypeError(
            "Each temporal observation must be a mapping."
        )


    if (
        observation.get(
            "validated_observation"
        )
        is not True
    ):

        raise ValueError(
            "Temporal window accepts only "
            "validated_observation=True records."
        )


    if (
        observation.get(
            "risk_status"
        )
        != "SCORE_AVAILABLE"
    ):

        raise ValueError(
            "Temporal window requires "
            "risk_status='SCORE_AVAILABLE'."
        )


    timestamp = _parse_timestamp(
        observation.get(
            "timestamp"
        )
    )


    score = _validate_score(
        observation.get(
            "stress_risk_score"
        )
    )


    plant_id = observation.get(
        "plant_id"
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


    return {
        "plant_id":
            plant_id,

        "timestamp":
            timestamp,

        "timestamp_iso":
            timestamp.isoformat(),

        "stress_risk_score":
            score,

        "sensor_values":
            _extract_sensor_values(
                observation
            ),
    }


def _validated_window(
    observations: Sequence[
        Mapping[str, Any]
    ],
    *,
    window_size: int,
) -> list[dict[str, Any]]:

    window_size = int(
        window_size
    )

    if window_size < 3:

        raise ValueError(
            "window_size must be >= 3."
        )


    if len(
        observations
    ) < 1:

        raise ValueError(
            "At least one observation is required."
        )


    validated = [
        _validate_observation(
            observation
        )
        for observation in observations
    ]


    plant_ids = {
        item[
            "plant_id"
        ]
        for item in validated
    }


    if len(
        plant_ids
    ) != 1:

        raise ValueError(
            "Temporal window cannot mix plant identities."
        )


    validated.sort(
        key=lambda item:
            item[
                "timestamp"
            ]
    )


    timestamps = [
        item[
            "timestamp"
        ]
        for item in validated
    ]


    if len(
        set(
            timestamps
        )
    ) != len(
        timestamps
    ):

        raise ValueError(
            "Duplicate timestamps are not allowed."
        )


    return validated[
        -window_size:
    ]


def _hours_between(
    earlier: datetime,
    later: datetime,
) -> float:

    seconds = (
        later
        - earlier
    ).total_seconds()


    if seconds <= 0:

        raise ValueError(
            "Temporal timestamps must increase."
        )


    return (
        seconds
        / 3600.0
    )


def _velocity(
    first_value: float,
    first_time: datetime,
    second_value: float,
    second_time: datetime,
) -> float:

    hours = _hours_between(
        first_time,
        second_time,
    )


    return (
        (
            second_value
            - first_value
        )
        / hours
    )


def _trend_state(
    velocity: float,
    *,
    deadband: float,
) -> str:

    deadband = _finite_float(
        deadband,
        "trend_deadband",
    )


    if deadband < 0:

        raise ValueError(
            "trend deadband must be >= 0."
        )


    if velocity > deadband:

        return "RISING"


    if velocity < (
        -deadband
    ):

        return "FALLING"


    return "STABLE"


def _risk_dynamics(
    window: Sequence[
        Mapping[str, Any]
    ],
    *,
    risk_velocity_deadband: float,
) -> dict[str, Any]:

    if len(
        window
    ) < 2:

        return {
            "available":
                False,

            "trend":
                None,

            "trend_code":
                None,

            "velocity":
                None,

            "acceleration":
                None,
        }


    previous = window[-2]

    current = window[-1]


    current_velocity = _velocity(
        previous[
            "stress_risk_score"
        ],
        previous[
            "timestamp"
        ],
        current[
            "stress_risk_score"
        ],
        current[
            "timestamp"
        ],
    )


    trend = _trend_state(
        current_velocity,
        deadband=
            risk_velocity_deadband,
    )


    acceleration = None


    if len(
        window
    ) >= 3:

        first = window[-3]


        previous_velocity = _velocity(
            first[
                "stress_risk_score"
            ],
            first[
                "timestamp"
            ],
            previous[
                "stress_risk_score"
            ],
            previous[
                "timestamp"
            ],
        )


        first_interval = _hours_between(
            first[
                "timestamp"
            ],
            previous[
                "timestamp"
            ],
        )


        second_interval = _hours_between(
            previous[
                "timestamp"
            ],
            current[
                "timestamp"
            ],
        )


        midpoint_hours = (
            (
                first_interval
                + second_interval
            )
            / 2.0
        )


        acceleration = (
            (
                current_velocity
                - previous_velocity
            )
            / midpoint_hours
        )


    return {
        "available":
            True,

        "trend":
            trend,

        "trend_code":
            TREND_TO_CODE[
                trend
            ],

        "velocity":
            float(
                current_velocity
            ),

        "acceleration":
            (
                None
                if acceleration
                is None
                else float(
                    acceleration
                )
            ),

        "velocity_unit":
            "RISK_SCORE_POINTS_PER_HOUR",

        "acceleration_unit":
            "RISK_SCORE_POINTS_PER_HOUR_SQUARED",
    }


def _sensor_trends(
    window: Sequence[
        Mapping[str, Any]
    ],
    *,
    deadbands: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    result = {}


    for field in SENSOR_FIELDS:

        deadband = _finite_float(
            deadbands.get(
                field,
                0.0,
            ),
            f"{field}_deadband",
        )


        if deadband < 0:

            raise ValueError(
                f"{field} deadband must be >= 0."
            )


        available = [
            item
            for item in window
            if (
                item[
                    "sensor_values"
                ].get(
                    field
                )
                is not None
            )
        ]


        if len(
            available
        ) < 2:

            result[
                field
            ] = {
                "available":
                    False,

                "trend":
                    None,

                "velocity":
                    None,
            }

            continue


        first = available[-2]

        current = available[-1]


        velocity = _velocity(
            first[
                "sensor_values"
            ][field],
            first[
                "timestamp"
            ],
            current[
                "sensor_values"
            ][field],
            current[
                "timestamp"
            ],
        )


        result[
            field
        ] = {
            "available":
                True,

            "trend":
                _trend_state(
                    velocity,
                    deadband=
                        deadband,
                ),

            "velocity":
                float(
                    velocity
                ),

            "deadband":
                float(
                    deadband
                ),

            "velocity_unit":
                (
                    "VALUE_UNITS_PER_HOUR"
                ),
        }


    return result


def _validated_action_threshold(
    artifact: Optional[
        Mapping[str, Any]
    ],
) -> Optional[float]:

    if artifact is None:

        return None


    if not isinstance(
        artifact,
        Mapping,
    ):

        raise ValueError(
            "Threshold artifact must be a mapping."
        )


    if (
        artifact.get(
            "schema_version"
        )
        != EXPECTED_RISK_CALIBRATION_SCHEMA
    ):

        raise ValueError(
            "Unsupported threshold artifact schema."
        )


    if (
        artifact.get(
            "status"
        )
        != "VALIDATED"
    ):

        return None


    candidates = artifact.get(
        "threshold_candidates"
    )


    if not isinstance(
        candidates,
        Mapping,
    ):

        raise ValueError(
            "Validated artifact missing threshold candidates."
        )


    thresholds = candidates.get(
        "thresholds"
    )


    if not isinstance(
        thresholds,
        Mapping,
    ):

        raise ValueError(
            "Validated artifact missing thresholds."
        )


    action = thresholds.get(
        "ACTION"
    )


    if not isinstance(
        action,
        Mapping,
    ):

        raise ValueError(
            "Validated artifact missing ACTION threshold."
        )


    threshold_probability = (
        _finite_float(
            action.get(
                "threshold"
            ),
            "ACTION threshold",
        )
    )


    if not (
        0.0
        <= threshold_probability
        <= 1.0
    ):

        raise ValueError(
            "ACTION threshold must be in [0, 1]."
        )


    return (
        threshold_probability
        * 100.0
    )


def _consistency_state(
    window: Sequence[
        Mapping[str, Any]
    ],
    *,
    risk_trend: Optional[str],
    threshold_artifact: Optional[
        Mapping[str, Any]
    ],
    confirmation_count: int,
) -> dict[str, Any]:

    confirmation_count = int(
        confirmation_count
    )


    if confirmation_count < 2:

        raise ValueError(
            "confirmation_count must be >= 2."
        )


    action_score = (
        _validated_action_threshold(
            threshold_artifact
        )
    )


    if action_score is None:

        return {
            "state":
                "RECHECK",

            "code":
                CONSISTENCY_TO_CODE[
                    "RECHECK"
                ],

            "reason":
                "VALIDATED_ACTION_THRESHOLD_UNAVAILABLE",

            "action_threshold_score":
                None,
        }


    if len(
        window
    ) < confirmation_count:

        return {
            "state":
                "RECHECK",

            "code":
                CONSISTENCY_TO_CODE[
                    "RECHECK"
                ],

            "reason":
                "INSUFFICIENT_CONFIRMATION_HISTORY",

            "action_threshold_score":
                float(
                    action_score
                ),
        }


    recent = window[
        -confirmation_count:
    ]


    all_at_or_above = all(
        item[
            "stress_risk_score"
        ]
        >= action_score
        for item in recent
    )


    if (
        all_at_or_above
        and risk_trend
        != "FALLING"
    ):

        return {
            "state":
                "CONFIRMED_STRESS",

            "code":
                CONSISTENCY_TO_CODE[
                    "CONFIRMED_STRESS"
                ],

            "reason":
                (
                    "REPEATED_VALIDATED_ACTION_LEVEL_"
                    "OBSERVATIONS"
                ),

            "action_threshold_score":
                float(
                    action_score
                ),
        }


    return {
        "state":
            "RECHECK",

        "code":
            CONSISTENCY_TO_CODE[
                "RECHECK"
            ],

        "reason":
            (
                "ACTION_LEVEL_CONFIRMATION_CRITERIA_"
                "NOT_MET"
            ),

        "action_threshold_score":
            float(
                action_score
            ),
    }


def build_temporal_features(
    observations: Sequence[
        Mapping[str, Any]
    ],
    *,
    window_size: int = 5,
    risk_velocity_deadband: float = 0.5,
    sensor_trend_deadbands: Optional[
        Mapping[str, Any]
    ] = None,
    threshold_artifact: Optional[
        Mapping[str, Any]
    ] = None,
    confirmation_count: int = 2,
) -> dict[str, Any]:

    window = _validated_window(
        observations,
        window_size=
            window_size,
    )


    risk = _risk_dynamics(
        window,
        risk_velocity_deadband=
            risk_velocity_deadband,
    )


    sensors = _sensor_trends(
        window,
        deadbands=(
            {}
            if sensor_trend_deadbands
            is None
            else sensor_trend_deadbands
        ),
    )


    consistency = (
        _consistency_state(
            window,
            risk_trend=
                risk.get(
                    "trend"
                ),
            threshold_artifact=
                threshold_artifact,
            confirmation_count=
                confirmation_count,
        )
    )


    latest = window[-1]


    # Layer 22 should only receive this temporal vector
    # when all core temporal derivatives exist.
    full_temporal_available = (
        len(
            window
        ) >= 3
        and risk[
            "available"
        ]
        and risk[
            "acceleration"
        ]
        is not None
    )


    feature_vector = None


    if full_temporal_available:

        values = [
            float(
                risk[
                    "trend_code"
                ]
            ),

            float(
                risk[
                    "velocity"
                ]
            ),

            float(
                risk[
                    "acceleration"
                ]
            ),

            float(
                consistency[
                    "code"
                ]
            ),
        ]


        if not all(
            math.isfinite(
                value
            )
            for value in values
        ):

            raise ValueError(
                "Temporal vector contains non-finite values."
            )


        feature_vector = {
            "names":
                list(
                    FEATURE_VECTOR_NAMES
                ),

            "values":
                values,

            "length":
                len(
                    FEATURE_VECTOR_NAMES
                ),
        }


    return {
        "schema_version":
            SCHEMA_VERSION,

        "feature_vector_version":
            FEATURE_VECTOR_VERSION,

        "status":
            (
                "TEMPORAL_FEATURES_AVAILABLE"
                if full_temporal_available
                else
                "INSUFFICIENT_HISTORY"
            ),

        "plant_id":
            latest[
                "plant_id"
            ],

        "timestamp":
            latest[
                "timestamp_iso"
            ],

        "window": {
            "configured_size":
                int(
                    window_size
                ),

            "used_observations":
                len(
                    window
                ),

            "minimum_for_velocity":
                2,

            "minimum_for_acceleration":
                3,

            "all_observations_validated":
                True,
        },

        "risk_dynamics":
            risk,

        "sensor_trends":
            sensors,

        "temporal_consistency":
            consistency,

        "feature_vector":
            feature_vector,

        "scientific_guardrails": {
            "heavy_temporal_neural_model_used":
                False,

            "validated_observations_only":
                True,

            "candidate_threshold_can_confirm_stress":
                False,

            "confirmed_stress_requires_validated_action_threshold":
                True,

            "temporal_state_authorizes_physical_action":
                False,

            "physical_action_authorized":
                False,

            "real_temporal_performance_validated":
                False,
        },
    }
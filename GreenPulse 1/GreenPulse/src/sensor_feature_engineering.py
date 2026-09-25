from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence
import math

from src.sensor_contract_guard import check_sensor_contract
from src.sensor_validator import validate_sensor


SCHEMA_VERSION = "greenpulse.sensor_feature_engineering.v1"
FEATURE_VECTOR_VERSION = "sensor_feature_vector_v1"
NORMALIZATION_SCHEMA_VERSION = "greenpulse.sensor_normalization.v1"

SENSOR_FIELDS = (
    "soil_moisture_pct",
    "temperature_c",
    "humidity_pct",
)

RATE_FEATURES = (
    "soil_moisture_change_per_hour",
    "temperature_change_per_hour",
    "humidity_change_per_hour",
)

FEATURE_NAMES = [
    "soil_moisture_pct",
    "temperature_c",
    "humidity_pct",

    "rolling_soil_moisture_pct",
    "rolling_temperature_c",
    "rolling_humidity_pct",
    "rolling_available",

    "soil_moisture_baseline_delta",
    "temperature_baseline_delta",
    "humidity_baseline_delta",
    "baseline_available",

    "soil_moisture_change_per_hour",
    "temperature_change_per_hour",
    "humidity_change_per_hour",
    "rate_available",

    "soil_moisture_trend_code",
    "temperature_trend_code",
    "humidity_trend_code",

    "source_is_simulated",
]


def _parse_time(value: str) -> datetime:

    dt = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    if dt.tzinfo is None:
        raise ValueError(
            "Timestamp timezone is required."
        )

    return dt.astimezone(
        timezone.utc
    )


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


def _validate_current_packet(
    packet: Mapping[str, Any],
) -> tuple[str, str]:

    valid, errors = check_sensor_contract(
        dict(
            packet
        )
    )

    if not valid:
        raise ValueError(
            "Invalid current sensor packet: "
            + "; ".join(
                errors
            )
        )

    status, reason = validate_sensor(
        dict(
            packet
        )
    )

    if status not in (
        "VALID",
        "VALID_SIMULATED",
    ):
        raise ValueError(
            f"Current sensor rejected: "
            f"{status}, {reason}"
        )

    return (
        status,
        reason,
    )


def _eligible_history(
    current: Mapping[str, Any],
    observations: Sequence[
        Mapping[str, Any]
    ],
    *,
    current_status: str,
    window_minutes: int,
) -> list[dict[str, Any]]:

    current_time = _parse_time(
        current[
            "timestamp"
        ]
    )

    eligible = []

    for observation in observations:

        if not isinstance(
            observation,
            Mapping,
        ):
            continue

        sensor_wrapper = (
            observation.get(
                "sensor"
            )
            or {}
        )

        packet = sensor_wrapper.get(
            "data"
        )

        if not isinstance(
            packet,
            Mapping,
        ):
            continue

        if sensor_wrapper.get(
            "status"
        ) != current_status:
            continue

        valid, _ = check_sensor_contract(
            dict(
                packet
            )
        )

        if not valid:
            continue

        if (
            packet.get(
                "plant_id"
            )
            != current[
                "plant_id"
            ]
        ):
            continue

        if (
            packet.get(
                "source"
            )
            != current[
                "source"
            ]
        ):
            continue

        if (
            packet.get(
                "soil_calibrated"
            )
            != current[
                "soil_calibrated"
            ]
        ):
            continue

        try:
            timestamp = _parse_time(
                packet[
                    "timestamp"
                ]
            )

        except (
            ValueError,
            TypeError,
            AttributeError,
            KeyError,
        ):
            continue

        age_seconds = (
            current_time
            - timestamp
        ).total_seconds()

        if not (
            0
            < age_seconds
            <= window_minutes * 60
        ):
            continue

        eligible.append({
            "timestamp":
                timestamp,

            "packet":
                dict(
                    packet
                ),
        })

    eligible.sort(
        key=lambda item: (
            item[
                "timestamp"
            ],
            repr(
                sorted(
                    item[
                        "packet"
                    ].items()
                )
            ),
        )
    )

    deduplicated = []

    seen_timestamps = {}

    for item in eligible:

        timestamp = item[
            "timestamp"
        ]

        packet = item[
            "packet"
        ]

        if timestamp in seen_timestamps:

            if (
                seen_timestamps[
                    timestamp
                ]
                != packet
            ):
                raise ValueError(
                    "HISTORY_TIMESTAMP_CONFLICT"
                )

            continue

        seen_timestamps[
            timestamp
        ] = packet

        deduplicated.append(
            item
        )

    return deduplicated


def _sample_mean(
    values: Sequence[float],
) -> float:

    ordered = sorted(
        _finite_float(
            value,
            "rolling value",
        )
        for value in values
    )

    if not ordered:
        raise ValueError(
            "Cannot average empty sequence."
        )

    return float(
        math.fsum(
            ordered
        )
        / len(
            ordered
        )
    )


def _rolling_statistics(
    current: Mapping[str, Any],
    history: Sequence[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    packets = [
        item[
            "packet"
        ]
        for item in history
    ]

    packets.append(
        dict(
            current
        )
    )

    if len(
        packets
    ) < 3:

        return {
            "available":
                False,

            "sample_count":
                len(
                    packets
                ),

            "average_type":
                "SAMPLE_MEAN",

            "soil_moisture_pct":
                None,

            "temperature_c":
                None,

            "humidity_pct":
                None,
        }

    return {
        "available":
            True,

        "sample_count":
            len(
                packets
            ),

        "average_type":
            "SAMPLE_MEAN",

        "soil_moisture_pct":
            _sample_mean([
                packet[
                    "soil_moisture_pct"
                ]
                for packet in packets
            ]),

        "temperature_c":
            _sample_mean([
                packet[
                    "temperature_c"
                ]
                for packet in packets
            ]),

        "humidity_pct":
            _sample_mean([
                packet[
                    "humidity_pct"
                ]
                for packet in packets
            ]),
    }


def _rate_features(
    current: Mapping[str, Any],
    history: Sequence[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    if not history:

        return {
            "available":
                False,

            "interval_seconds":
                None,

            "soil_moisture_change_per_hour":
                None,

            "temperature_change_per_hour":
                None,

            "humidity_change_per_hour":
                None,
        }

    previous = history[
        -1
    ][
        "packet"
    ]

    current_time = _parse_time(
        current[
            "timestamp"
        ]
    )

    previous_time = _parse_time(
        previous[
            "timestamp"
        ]
    )

    interval_seconds = (
        current_time
        - previous_time
    ).total_seconds()

    if not (
        60
        <= interval_seconds
        <= 3600
    ):

        return {
            "available":
                False,

            "interval_seconds":
                interval_seconds,

            "soil_moisture_change_per_hour":
                None,

            "temperature_change_per_hour":
                None,

            "humidity_change_per_hour":
                None,
        }

    factor = (
        3600.0
        / interval_seconds
    )

    return {
        "available":
            True,

        "interval_seconds":
            float(
                interval_seconds
            ),

        "soil_moisture_change_per_hour":
            (
                _finite_float(
                    current[
                        "soil_moisture_pct"
                    ],
                    "soil_moisture_pct",
                )
                -
                _finite_float(
                    previous[
                        "soil_moisture_pct"
                    ],
                    "previous soil_moisture_pct",
                )
            )
            * factor,

        "temperature_change_per_hour":
            (
                _finite_float(
                    current[
                        "temperature_c"
                    ],
                    "temperature_c",
                )
                -
                _finite_float(
                    previous[
                        "temperature_c"
                    ],
                    "previous temperature_c",
                )
            )
            * factor,

        "humidity_change_per_hour":
            (
                _finite_float(
                    current[
                        "humidity_pct"
                    ],
                    "humidity_pct",
                )
                -
                _finite_float(
                    previous[
                        "humidity_pct"
                    ],
                    "previous humidity_pct",
                )
            )
            * factor,
    }


def _baseline_delta(
    current: Mapping[str, Any],
    baseline: Optional[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    if baseline is None:

        return {
            "available":
                False,

            "baseline_version":
                None,

            "soil_moisture_delta":
                None,

            "temperature_delta":
                None,

            "humidity_delta":
                None,
        }

    required = [
        "version",
        "soil_moisture_pct",
        "temperature_c",
        "humidity_pct",
    ]

    missing = [
        key
        for key in required
        if key not in baseline
    ]

    if missing:

        raise ValueError(
            "Sensor baseline missing fields: "
            + ", ".join(
                missing
            )
        )

    return {
        "available":
            True,

        "baseline_version":
            str(
                baseline[
                    "version"
                ]
            ),

        "soil_moisture_delta":
            (
                _finite_float(
                    current[
                        "soil_moisture_pct"
                    ],
                    "soil_moisture_pct",
                )
                -
                _finite_float(
                    baseline[
                        "soil_moisture_pct"
                    ],
                    "baseline soil_moisture_pct",
                )
            ),

        "temperature_delta":
            (
                _finite_float(
                    current[
                        "temperature_c"
                    ],
                    "temperature_c",
                )
                -
                _finite_float(
                    baseline[
                        "temperature_c"
                    ],
                    "baseline temperature_c",
                )
            ),

        "humidity_delta":
            (
                _finite_float(
                    current[
                        "humidity_pct"
                    ],
                    "humidity_pct",
                )
                -
                _finite_float(
                    baseline[
                        "humidity_pct"
                    ],
                    "baseline humidity_pct",
                )
            ),
    }


def _trend_state(
    rate: Optional[float],
    deadband: float,
) -> tuple[str, float]:

    if rate is None:
        return (
            "INSUFFICIENT_HISTORY",
            0.0,
        )

    rate = _finite_float(
        rate,
        "rate",
    )

    deadband = _finite_float(
        deadband,
        "deadband",
    )

    if deadband < 0:
        raise ValueError(
            "Trend deadband cannot be negative."
        )

    if rate > deadband:
        return (
            "RISING",
            1.0,
        )

    if rate < -deadband:
        return (
            "FALLING",
            -1.0,
        )

    return (
        "STABLE",
        0.0,
    )


def _apply_normalization(
    raw_values: Sequence[float],
    artifact: Optional[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    raw_values = [
        _finite_float(
            value,
            "feature vector value",
        )
        for value in raw_values
    ]

    if artifact is None:

        return {
            "applied":
                False,

            "artifact_version":
                None,

            "values":
                raw_values,
        }

    if (
        artifact.get(
            "schema_version"
        )
        != NORMALIZATION_SCHEMA_VERSION
    ):

        raise ValueError(
            "Unsupported normalization schema."
        )

    if (
        artifact.get(
            "feature_vector_version"
        )
        != FEATURE_VECTOR_VERSION
    ):

        raise ValueError(
            "Normalization artifact feature "
            "version mismatch."
        )

    parameters = artifact.get(
        "parameters"
    )

    if not isinstance(
        parameters,
        Mapping,
    ):
        raise ValueError(
            "Normalization parameters missing."
        )

    normalized = []

    for name, raw in zip(
        FEATURE_NAMES,
        raw_values,
    ):

        if name not in parameters:

            raise ValueError(
                "Normalization parameter missing: "
                + name
            )

        item = parameters[
            name
        ]

        center = _finite_float(
            item[
                "center"
            ],
            f"{name}.center",
        )

        scale = _finite_float(
            item[
                "scale"
            ],
            f"{name}.scale",
        )

        if scale <= 0:

            raise ValueError(
                f"{name}.scale must be > 0."
            )

        normalized.append(
            float(
                (
                    raw
                    - center
                )
                / scale
            )
        )

    return {
        "applied":
            True,

        "artifact_version":
            str(
                artifact.get(
                    "version",
                    "UNSPECIFIED",
                )
            ),

        "values":
            normalized,
    }


def build_sensor_feature_vector(
    current_packet: Mapping[
        str,
        Any,
    ],
    observations: Sequence[
        Mapping[str, Any]
    ],
    *,
    baseline: Optional[
        Mapping[str, Any]
    ] = None,
    normalization_artifact: Optional[
        Mapping[str, Any]
    ] = None,
    window_minutes: int = 30,
    trend_deadbands: Optional[
        Mapping[str, float]
    ] = None,
) -> dict[str, Any]:

    if not (
        1
        <= int(
            window_minutes
        )
        <= 60
    ):
        raise ValueError(
            "window_minutes must be in [1, 60]."
        )

    current = dict(
        current_packet
    )

    current_status, current_reason = (
        _validate_current_packet(
            current
        )
    )

    history = _eligible_history(
        current,
        observations,
        current_status=current_status,
        window_minutes=int(
            window_minutes
        ),
    )

    rolling = _rolling_statistics(
        current,
        history,
    )

    rates = _rate_features(
        current,
        history,
    )

    baseline_delta = _baseline_delta(
        current,
        baseline,
    )

    deadbands = {
        "soil_moisture":
            0.0,

        "temperature":
            0.0,

        "humidity":
            0.0,
    }

    if trend_deadbands is not None:

        for key in deadbands:

            if key in trend_deadbands:

                deadbands[
                    key
                ] = _finite_float(
                    trend_deadbands[
                        key
                    ],
                    f"{key} deadband",
                )

    soil_state, soil_code = (
        _trend_state(
            rates[
                "soil_moisture_change_per_hour"
            ],
            deadbands[
                "soil_moisture"
            ],
        )
    )

    temperature_state, temperature_code = (
        _trend_state(
            rates[
                "temperature_change_per_hour"
            ],
            deadbands[
                "temperature"
            ],
        )
    )

    humidity_state, humidity_code = (
        _trend_state(
            rates[
                "humidity_change_per_hour"
            ],
            deadbands[
                "humidity"
            ],
        )
    )

    rolling_soil = (
        rolling[
            "soil_moisture_pct"
        ]
        if rolling[
            "available"
        ]
        else 0.0
    )

    rolling_temperature = (
        rolling[
            "temperature_c"
        ]
        if rolling[
            "available"
        ]
        else 0.0
    )

    rolling_humidity = (
        rolling[
            "humidity_pct"
        ]
        if rolling[
            "available"
        ]
        else 0.0
    )

    baseline_soil = (
        baseline_delta[
            "soil_moisture_delta"
        ]
        if baseline_delta[
            "available"
        ]
        else 0.0
    )

    baseline_temperature = (
        baseline_delta[
            "temperature_delta"
        ]
        if baseline_delta[
            "available"
        ]
        else 0.0
    )

    baseline_humidity = (
        baseline_delta[
            "humidity_delta"
        ]
        if baseline_delta[
            "available"
        ]
        else 0.0
    )

    soil_rate = (
        rates[
            "soil_moisture_change_per_hour"
        ]
        if rates[
            "available"
        ]
        else 0.0
    )

    temperature_rate = (
        rates[
            "temperature_change_per_hour"
        ]
        if rates[
            "available"
        ]
        else 0.0
    )

    humidity_rate = (
        rates[
            "humidity_change_per_hour"
        ]
        if rates[
            "available"
        ]
        else 0.0
    )

    raw_values = [
        _finite_float(
            current[
                "soil_moisture_pct"
            ],
            "soil_moisture_pct",
        ),

        _finite_float(
            current[
                "temperature_c"
            ],
            "temperature_c",
        ),

        _finite_float(
            current[
                "humidity_pct"
            ],
            "humidity_pct",
        ),

        float(
            rolling_soil
        ),

        float(
            rolling_temperature
        ),

        float(
            rolling_humidity
        ),

        float(
            rolling[
                "available"
            ]
        ),

        float(
            baseline_soil
        ),

        float(
            baseline_temperature
        ),

        float(
            baseline_humidity
        ),

        float(
            baseline_delta[
                "available"
            ]
        ),

        float(
            soil_rate
        ),

        float(
            temperature_rate
        ),

        float(
            humidity_rate
        ),

        float(
            rates[
                "available"
            ]
        ),

        float(
            soil_code
        ),

        float(
            temperature_code
        ),

        float(
            humidity_code
        ),

        float(
            current[
                "source"
            ]
            == "SIMULATED"
        ),
    ]

    if len(
        raw_values
    ) != len(
        FEATURE_NAMES
    ):

        raise RuntimeError(
            "Sensor feature-vector schema mismatch."
        )

    normalized = _apply_normalization(
        raw_values,
        normalization_artifact,
    )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "feature_vector_version":
            FEATURE_VECTOR_VERSION,

        "plant_id":
            current[
                "plant_id"
            ],

        "timestamp":
            current[
                "timestamp"
            ],

        "provenance": {
            "source":
                current[
                    "source"
                ],

            "sensor_validation_status":
                current_status,

            "sensor_validation_reason":
                current_reason,

            "device_authenticated":
                False,

            "soil_calibrated":
                bool(
                    current[
                        "soil_calibrated"
                    ]
                ),
        },

        "current": {
            key:
                float(
                    current[
                        key
                    ]
                )
            for key in SENSOR_FIELDS
        },

        "rolling_window": {
            **rolling,

            "window_minutes":
                int(
                    window_minutes
                ),
        },

        "baseline_delta":
            baseline_delta,

        "rate_of_change":
            rates,

        "trend": {
            "soil_moisture":
                soil_state,

            "temperature":
                temperature_state,

            "humidity":
                humidity_state,

            "deadbands":
                deadbands,
        },

        "feature_vector": {
            "names":
                list(
                    FEATURE_NAMES
                ),

            "raw_values":
                raw_values,

            "values":
                normalized[
                    "values"
                ],

            "length":
                len(
                    FEATURE_NAMES
                ),

            "normalization_applied":
                normalized[
                    "applied"
                ],

            "normalization_artifact_version":
                normalized[
                    "artifact_version"
                ],

            "missing_numeric_policy":
                (
                    "Unavailable derived numeric features "
                    "are encoded as 0.0 only together with "
                    "an explicit availability feature."
                ),

            "units": {
                "soil_moisture_pct":
                    "percent",

                "temperature_c":
                    "degC",

                "humidity_pct":
                    "percent",

                "rolling_soil_moisture_pct":
                    "percent",

                "rolling_temperature_c":
                    "degC",

                "rolling_humidity_pct":
                    "percent",

                "soil_moisture_baseline_delta":
                    "percentage_points",

                "temperature_baseline_delta":
                    "degC",

                "humidity_baseline_delta":
                    "percentage_points",

                "soil_moisture_change_per_hour":
                    "percentage_points_per_hour",

                "temperature_change_per_hour":
                    "degC_per_hour",

                "humidity_change_per_hour":
                    "percentage_points_per_hour",

                "trend_codes":
                    {
                        "-1":
                            "FALLING",

                        "0":
                            "STABLE_OR_UNAVAILABLE",

                        "1":
                            "RISING",
                    },
            },
        },

        "scientific_guardrails": {
            "simulated_sensor_is_real_sensor_evidence":
                False,

            "device_source_field_is_authentication":
                False,

            "sensor_features_are_water_stress_probability":
                False,

            "trend_is_early_stress_proof":
                False,

            "normalization_fitted_on_current_packet":
                False,

            "physical_action_authorized":
                False,
        },
    }
from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = (
    "greenpulse.system_drift_monitor.v1"
)

POLICY_SCHEMA_VERSION = (
    "greenpulse.drift_monitoring_policy.v1"
)


def _numeric_values(
    values: Sequence[float],
    name: str,
) -> list[float]:

    result = [
        float(value)
        for value in values
    ]

    if not result:
        raise ValueError(
            f"{name} must not be empty."
        )

    return result


def numeric_summary(
    values: Sequence[float],
) -> dict[str, float | int]:

    data = _numeric_values(
        values,
        "values",
    )

    mean = sum(data) / len(data)

    variance = (
        sum(
            (value - mean) ** 2
            for value in data
        )
        / len(data)
    )

    return {
        "count":
            len(data),

        "mean":
            mean,

        "std":
            sqrt(variance),

        "min":
            min(data),

        "max":
            max(data),
    }


def categorical_distribution(
    values: Sequence[str],
) -> dict[str, float]:

    items = [
        str(value)
        for value in values
    ]

    if not items:
        raise ValueError(
            "Categorical values must not be empty."
        )

    total = len(items)

    counts: dict[str, int] = {}

    for item in items:
        counts[item] = (
            counts.get(item, 0)
            + 1
        )

    return {
        key:
            count / total

        for key, count
        in sorted(
            counts.items()
        )
    }


def total_variation_distance(
    baseline: Mapping[str, float],
    current: Mapping[str, float],
) -> float:

    labels = (
        set(baseline)
        | set(current)
    )

    return 0.5 * sum(
        abs(
            float(
                baseline.get(
                    label,
                    0.0,
                )
            )
            - float(
                current.get(
                    label,
                    0.0,
                )
            )
        )
        for label in labels
    )


def relative_mean_shift(
    baseline_mean: float,
    current_mean: float,
) -> float:

    denominator = max(
        abs(
            float(
                baseline_mean
            )
        ),
        1e-9,
    )

    return (
        abs(
            float(
                current_mean
            )
            - float(
                baseline_mean
            )
        )
        / denominator
    )


def validate_policy(
    policy: Mapping[str, Any],
) -> None:

    if (
        policy.get(
            "schema_version"
        )
        != POLICY_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported drift monitoring policy schema."
        )

    thresholds = policy.get(
        "thresholds"
    )

    if not isinstance(
        thresholds,
        Mapping,
    ):
        raise ValueError(
            "thresholds missing."
        )

    required = (
        "confidence_mean_drop_absolute",
        "prediction_total_variation_distance",
        "risk_mean_relative_shift",
        "sensor_mean_relative_shift",
    )

    for key in required:

        value = thresholds.get(
            key
        )

        if value is None:
            raise ValueError(
                f"Missing threshold: {key}"
            )

        value = float(value)

        if value < 0:
            raise ValueError(
                f"{key} must be non-negative."
            )

    workflow = policy.get(
        "workflow"
    )

    if not isinstance(
        workflow,
        Mapping,
    ):
        raise ValueError(
            "workflow missing."
        )

    if (
        workflow.get(
            "automatic_model_deployment_allowed"
        )
        is not False
    ):
        raise ValueError(
            "Automatic unvalidated deployment must remain disabled."
        )


def evaluate_system_drift(
    *,
    policy: Mapping[str, Any],
    baseline: Mapping[str, Any] | None,
    current: Mapping[str, Any],
) -> dict[str, Any]:

    validate_policy(
        policy
    )

    if not isinstance(
        current,
        Mapping,
    ):
        raise ValueError(
            "current must be a mapping."
        )

    original_current = deepcopy(
        current
    )

    thresholds = policy[
        "thresholds"
    ]

    runtime_errors = list(
        current.get(
            "runtime_errors",
            [],
        )
    )

    resource_metrics = deepcopy(
        current.get(
            "resource_metrics",
            {},
        )
    )

    monitoring = {
        "runtime_errors": {
            "count":
                len(
                    runtime_errors
                ),

            "items":
                runtime_errors,
        },

        "resource_metrics":
            resource_metrics,
    }

    if baseline is None:

        if current != original_current:
            raise RuntimeError(
                "Current monitoring input mutated."
            )

        return {
            "schema_version":
                SCHEMA_VERSION,

            "status":
                "BASELINE_REQUIRED",

            "monitoring":
                monitoring,

            "drift": {
                "evaluated":
                    False,

                "warnings":
                    [],
            },

            "workflow": {
                "review_required":
                    False,

                "retraining_review_required":
                    False,

                "automatic_model_deployment_allowed":
                    False,
            },

            "claim_boundary": {
                "real_production_baseline_used":
                    False,

                "real_drift_validated":
                    False,

                "automatic_unvalidated_deployment":
                    False,
            },
        }

    if not isinstance(
        baseline,
        Mapping,
    ):
        raise ValueError(
            "baseline must be a mapping or None."
        )

    original_baseline = deepcopy(
        baseline
    )

    baseline_predictions = (
        categorical_distribution(
            baseline[
                "prediction_labels"
            ]
        )
    )

    current_predictions = (
        categorical_distribution(
            current[
                "prediction_labels"
            ]
        )
    )

    prediction_tvd = (
        total_variation_distance(
            baseline_predictions,
            current_predictions,
        )
    )

    baseline_confidence = numeric_summary(
        baseline[
            "confidences"
        ]
    )

    current_confidence = numeric_summary(
        current[
            "confidences"
        ]
    )

    confidence_drop = max(
        0.0,
        baseline_confidence[
            "mean"
        ]
        - current_confidence[
            "mean"
        ],
    )

    baseline_risk = numeric_summary(
        baseline[
            "risks"
        ]
    )

    current_risk = numeric_summary(
        current[
            "risks"
        ]
    )

    risk_shift = relative_mean_shift(
        baseline_risk[
            "mean"
        ],
        current_risk[
            "mean"
        ],
    )

    baseline_sensors = baseline.get(
        "sensors",
        {},
    )

    current_sensors = current.get(
        "sensors",
        {},
    )

    sensor_results = {}

    common_sensors = sorted(
        set(
            baseline_sensors
        )
        & set(
            current_sensors
        )
    )

    for sensor_name in common_sensors:

        baseline_summary = numeric_summary(
            baseline_sensors[
                sensor_name
            ]
        )

        current_summary = numeric_summary(
            current_sensors[
                sensor_name
            ]
        )

        shift = relative_mean_shift(
            baseline_summary[
                "mean"
            ],
            current_summary[
                "mean"
            ],
        )

        sensor_results[
            sensor_name
        ] = {
            "baseline":
                baseline_summary,

            "current":
                current_summary,

            "relative_mean_shift":
                shift,

            "warning":
                (
                    shift
                    >= float(
                        thresholds[
                            "sensor_mean_relative_shift"
                        ]
                    )
                ),
        }

    warnings = []

    if (
        confidence_drop
        >= float(
            thresholds[
                "confidence_mean_drop_absolute"
            ]
        )
    ):
        warnings.append(
            {
                "code":
                    "CONFIDENCE_DROP",

                "action":
                    "REVIEW_RETRAINING_WORKFLOW",
            }
        )

    if (
        prediction_tvd
        >= float(
            thresholds[
                "prediction_total_variation_distance"
            ]
        )
    ):
        warnings.append(
            {
                "code":
                    "PREDICTION_DISTRIBUTION_SHIFT",

                "action":
                    "REVIEW_RETRAINING_WORKFLOW",
            }
        )

    if (
        risk_shift
        >= float(
            thresholds[
                "risk_mean_relative_shift"
            ]
        )
    ):
        warnings.append(
            {
                "code":
                    "RISK_DISTRIBUTION_SHIFT",

                "action":
                    "REVIEW_RETRAINING_WORKFLOW",
            }
        )

    shifted_sensors = [
        sensor_name
        for sensor_name, result
        in sensor_results.items()
        if result[
            "warning"
        ]
    ]

    if shifted_sensors:
        warnings.append(
            {
                "code":
                    "FEATURE_DISTRIBUTION_CHANGE",

                "sensors":
                    shifted_sensors,

                "action":
                    "REVIEW_RETRAINING_WORKFLOW",
            }
        )

    review_required = bool(
        warnings
    )

    if (
        baseline != original_baseline
        or current != original_current
    ):
        raise RuntimeError(
            "Monitoring inputs mutated."
        )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "status":
            (
                "DRIFT_WARNING"
                if review_required
                else "NO_DRIFT_WARNING"
            ),

        "monitoring":
            monitoring,

        "distributions": {
            "prediction": {
                "baseline":
                    baseline_predictions,

                "current":
                    current_predictions,

                "total_variation_distance":
                    prediction_tvd,
            },

            "confidence": {
                "baseline":
                    baseline_confidence,

                "current":
                    current_confidence,

                "absolute_mean_drop":
                    confidence_drop,
            },

            "risk": {
                "baseline":
                    baseline_risk,

                "current":
                    current_risk,

                "relative_mean_shift":
                    risk_shift,
            },

            "sensors":
                sensor_results,
        },

        "drift": {
            "evaluated":
                True,

            "warnings":
                warnings,
        },

        "workflow": {
            "review_required":
                review_required,

            "retraining_review_required":
                review_required,

            "automatic_model_deployment_allowed":
                False,
        },

        "claim_boundary": {
            "real_production_baseline_used":
                False,

            "real_drift_validated":
                False,

            "automatic_unvalidated_deployment":
                False,
        },
    }
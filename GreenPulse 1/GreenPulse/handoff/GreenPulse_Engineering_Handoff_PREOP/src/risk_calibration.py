from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

import math
import numpy as np


CALIBRATION_SCHEMA_VERSION = (
    "greenpulse.risk_calibration.v1"
)

CALIBRATOR_SCHEMA_VERSION = (
    "greenpulse.platt_calibrator.v1"
)

CANDIDATE_STATUS = "CANDIDATE_ONLY"


def _finite_float(
    value: Any,
    name: str,
) -> float:

    if isinstance(value, bool):
        raise ValueError(
            f"{name} must be numeric."
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"{name} must be finite."
        )

    return result


def _validate_probability(
    value: Any,
    name: str = "probability",
) -> float:

    result = _finite_float(
        value,
        name,
    )

    if not 0.0 <= result <= 1.0:
        raise ValueError(
            f"{name} must be in [0, 1]."
        )

    return result


def _binary_label(
    value: Any,
) -> int:

    if isinstance(value, bool):
        return int(value)

    if (
        isinstance(
            value,
            (int, np.integer),
        )
        and int(value) in (0, 1)
    ):
        return int(value)

    raise ValueError(
        "Labels must be binary 0/1."
    )


def _prepare(
    probabilities: Sequence[Any],
    labels: Sequence[Any],
    *,
    require_both_classes: bool,
) -> tuple[np.ndarray, np.ndarray]:

    if len(probabilities) != len(labels):
        raise ValueError(
            "Probability/label length mismatch."
        )

    if len(probabilities) < 1:
        raise ValueError(
            "At least one sample is required."
        )

    p = np.asarray(
        [
            _validate_probability(
                value
            )
            for value in probabilities
        ],
        dtype=np.float64,
    )

    y = np.asarray(
        [
            _binary_label(
                value
            )
            for value in labels
        ],
        dtype=np.float64,
    )

    if (
        require_both_classes
        and len(
            np.unique(y)
        ) < 2
    ):
        raise ValueError(
            "Both binary classes are required."
        )

    return p, y


def _canonical_order(
    probabilities: np.ndarray,
    labels: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:

    order = sorted(
        range(len(probabilities)),
        key=lambda index: (
            float(
                probabilities[index]
            ),
            float(
                labels[index]
            ),
        ),
    )

    indices = np.asarray(
        order,
        dtype=np.int64,
    )

    return (
        probabilities[indices],
        labels[indices],
    )


def _sigmoid(
    values: np.ndarray,
) -> np.ndarray:

    clipped = np.clip(
        values,
        -35.0,
        35.0,
    )

    return (
        1.0
        /
        (
            1.0
            + np.exp(-clipped)
        )
    )


def _logit(
    probabilities: np.ndarray,
) -> np.ndarray:

    clipped = np.clip(
        probabilities,
        1e-6,
        1.0 - 1e-6,
    )

    return np.log(
        clipped
        / (
            1.0
            - clipped
        )
    )


def calibration_metrics(
    probabilities: Sequence[Any],
    labels: Sequence[Any],
    *,
    bins: int = 10,
) -> dict[str, Any]:

    bins = int(bins)

    if bins < 2:
        raise ValueError(
            "bins must be >= 2."
        )

    p, y = _prepare(
        probabilities,
        labels,
        require_both_classes=False,
    )

    n = len(p)

    brier = math.fsum(
        float(
            (
                probability
                - label
            ) ** 2
        )
        for probability, label
        in zip(p, y)
    ) / n

    eps = 1e-12

    log_loss = -math.fsum(
        float(
            label
            * math.log(
                max(
                    probability,
                    eps,
                )
            )
            +
            (
                1.0
                - label
            )
            * math.log(
                max(
                    1.0
                    - probability,
                    eps,
                )
            )
        )
        for probability, label
        in zip(p, y)
    ) / n

    ece = 0.0

    bin_details = []

    for bin_index in range(bins):

        lower = (
            bin_index
            / bins
        )

        upper = (
            (
                bin_index
                + 1
            )
            / bins
        )

        if bin_index == bins - 1:

            mask = (
                (p >= lower)
                & (p <= upper)
            )

        else:

            mask = (
                (p >= lower)
                & (p < upper)
            )

        count = int(
            np.sum(mask)
        )

        if count == 0:
            continue

        confidence = math.fsum(
            float(value)
            for value in p[mask]
        ) / count

        observed_rate = math.fsum(
            float(value)
            for value in y[mask]
        ) / count

        gap = abs(
            confidence
            - observed_rate
        )

        ece += (
            count
            / n
        ) * gap

        bin_details.append(
            {
                "lower":
                    float(lower),

                "upper":
                    float(upper),

                "sample_count":
                    count,

                "mean_probability":
                    float(
                        confidence
                    ),

                "observed_positive_rate":
                    float(
                        observed_rate
                    ),

                "absolute_gap":
                    float(
                        gap
                    ),
            }
        )

    return {
        "sample_count":
            int(n),

        "brier_score":
            float(brier),

        "log_loss":
            float(log_loss),

        "expected_calibration_error":
            float(ece),

        "ece_bins":
            int(bins),

        "bin_details":
            bin_details,
    }


@dataclass
class PlattCalibrator:

    slope: float

    intercept: float

    iterations: int

    learning_rate: float

    l2_strength: float

    schema_version: str = (
        CALIBRATOR_SCHEMA_VERSION
    )


    def predict(
        self,
        probabilities: Sequence[Any],
    ) -> np.ndarray:

        p = np.asarray(
            [
                _validate_probability(
                    value
                )
                for value in probabilities
            ],
            dtype=np.float64,
        )

        logits = _logit(p)

        return _sigmoid(
            (
                self.slope
                * logits
            )
            + self.intercept
        )


    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "schema_version":
                self.schema_version,

            "method":
                "PLATT_SCALING",

            "slope":
                float(
                    self.slope
                ),

            "intercept":
                float(
                    self.intercept
                ),

            "training": {
                "iterations":
                    int(
                        self.iterations
                    ),

                "learning_rate":
                    float(
                        self.learning_rate
                    ),

                "l2_strength":
                    float(
                        self.l2_strength
                    ),
            },
        }


    @classmethod
    def from_dict(
        cls,
        payload: Mapping[
            str,
            Any,
        ],
    ) -> "PlattCalibrator":

        if (
            payload.get(
                "schema_version"
            )
            != CALIBRATOR_SCHEMA_VERSION
        ):
            raise ValueError(
                "Unsupported calibrator schema."
            )

        training = payload.get(
            "training"
        )

        if not isinstance(
            training,
            Mapping,
        ):
            raise ValueError(
                "Calibrator training metadata missing."
            )

        return cls(
            slope=
                _finite_float(
                    payload.get(
                        "slope"
                    ),
                    "slope",
                ),

            intercept=
                _finite_float(
                    payload.get(
                        "intercept"
                    ),
                    "intercept",
                ),

            iterations=
                int(
                    training.get(
                        "iterations"
                    )
                ),

            learning_rate=
                _finite_float(
                    training.get(
                        "learning_rate"
                    ),
                    "learning_rate",
                ),

            l2_strength=
                _finite_float(
                    training.get(
                        "l2_strength"
                    ),
                    "l2_strength",
                ),
        )


def fit_platt_calibrator(
    probabilities: Sequence[Any],
    labels: Sequence[Any],
    *,
    iterations: int = 2500,
    learning_rate: float = 0.01,
    l2_strength: float = 0.0001,
) -> PlattCalibrator:

    iterations = int(
        iterations
    )

    learning_rate = _finite_float(
        learning_rate,
        "learning_rate",
    )

    l2_strength = _finite_float(
        l2_strength,
        "l2_strength",
    )

    if iterations < 1:
        raise ValueError(
            "iterations must be >= 1."
        )

    if learning_rate <= 0:
        raise ValueError(
            "learning_rate must be > 0."
        )

    if l2_strength < 0:
        raise ValueError(
            "l2_strength must be >= 0."
        )

    p, y = _prepare(
        probabilities,
        labels,
        require_both_classes=True,
    )

    p, y = _canonical_order(
        p,
        y,
    )

    x = _logit(p)

    slope = 1.0

    intercept = 0.0

    n = float(
        len(x)
    )

    for _ in range(
        iterations
    ):

        calibrated = _sigmoid(
            (
                slope
                * x
            )
            + intercept
        )

        error = (
            calibrated
            - y
        )

        slope_gradient = (
            math.fsum(
                float(
                    err
                    * value
                )
                for err, value
                in zip(
                    error,
                    x,
                )
            )
            / n
        )

        slope_gradient += (
            l2_strength
            * slope
        )

        intercept_gradient = (
            math.fsum(
                float(value)
                for value in error
            )
            / n
        )

        slope -= (
            learning_rate
            * slope_gradient
        )

        intercept -= (
            learning_rate
            * intercept_gradient
        )

    return PlattCalibrator(
        slope=
            float(
                slope
            ),

        intercept=
            float(
                intercept
            ),

        iterations=
            iterations,

        learning_rate=
            float(
                learning_rate
            ),

        l2_strength=
            float(
                l2_strength
            ),
    )


def compare_calibration(
    calibrator: PlattCalibrator,
    probabilities: Sequence[Any],
    labels: Sequence[Any],
    *,
    bins: int = 10,
) -> dict[str, Any]:

    before = calibration_metrics(
        probabilities,
        labels,
        bins=bins,
    )

    calibrated = calibrator.predict(
        probabilities
    )

    after = calibration_metrics(
        calibrated.tolist(),
        labels,
        bins=bins,
    )

    return {
        "before":
            before,

        "after":
            after,

        "calibrated_probabilities":
            [
                float(value)
                for value in calibrated
            ],

        "improvement_is_claimed":
            False,

        "note":
            (
                "Metrics are descriptive for the supplied "
                "validation data only."
            ),
    }


def evaluate_threshold(
    probabilities: Sequence[Any],
    labels: Sequence[Any],
    *,
    threshold: float,
    false_negative_cost: float,
    false_positive_cost: float,
) -> dict[str, Any]:

    threshold = _validate_probability(
        threshold,
        "threshold",
    )

    false_negative_cost = (
        _finite_float(
            false_negative_cost,
            "false_negative_cost",
        )
    )

    false_positive_cost = (
        _finite_float(
            false_positive_cost,
            "false_positive_cost",
        )
    )

    if (
        false_negative_cost <= 0
        or false_positive_cost <= 0
    ):
        raise ValueError(
            "Threshold costs must be > 0."
        )

    p, y_float = _prepare(
        probabilities,
        labels,
        require_both_classes=False,
    )

    y = y_float.astype(
        np.int64
    )

    prediction = (
        p >= threshold
    ).astype(
        np.int64
    )

    tp = int(
        np.sum(
            (y == 1)
            & (prediction == 1)
        )
    )

    tn = int(
        np.sum(
            (y == 0)
            & (prediction == 0)
        )
    )

    fp = int(
        np.sum(
            (y == 0)
            & (prediction == 1)
        )
    )

    fn = int(
        np.sum(
            (y == 1)
            & (prediction == 0)
        )
    )

    precision = (
        tp / (tp + fp)
        if (
            tp + fp
        )
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if (
            tp + fn
        )
        else 0.0
    )

    false_positive_rate = (
        fp / (fp + tn)
        if (
            fp + tn
        )
        else 0.0
    )

    false_negative_rate = (
        fn / (fn + tp)
        if (
            fn + tp
        )
        else 0.0
    )

    intervention_rate = (
        int(
            np.sum(
                prediction == 1
            )
        )
        / len(y)
    )

    weighted_cost = (
        (
            fn
            * false_negative_cost
        )
        +
        (
            fp
            * false_positive_cost
        )
    ) / len(y)

    return {
        "threshold":
            float(
                threshold
            ),

        "sample_count":
            int(
                len(y)
            ),

        "true_positive":
            tp,

        "true_negative":
            tn,

        "false_positive":
            fp,

        "false_negative":
            fn,

        "precision":
            float(
                precision
            ),

        "recall":
            float(
                recall
            ),

        "false_positive_rate":
            float(
                false_positive_rate
            ),

        "false_negative_rate":
            float(
                false_negative_rate
            ),

        "intervention_rate":
            float(
                intervention_rate
            ),

        "weighted_error_cost":
            float(
                weighted_cost
            ),

        "policy_costs": {
            "false_negative_cost":
                float(
                    false_negative_cost
                ),

            "false_positive_cost":
                float(
                    false_positive_cost
                ),
        },
    }


def optimize_threshold(
    probabilities: Sequence[Any],
    labels: Sequence[Any],
    *,
    false_negative_cost: float,
    false_positive_cost: float,
    minimum_recall: Optional[
        float
    ] = None,
    minimum_precision: Optional[
        float
    ] = None,
) -> dict[str, Any]:

    p, y = _prepare(
        probabilities,
        labels,
        require_both_classes=True,
    )

    false_negative_cost = (
        _finite_float(
            false_negative_cost,
            "false_negative_cost",
        )
    )

    false_positive_cost = (
        _finite_float(
            false_positive_cost,
            "false_positive_cost",
        )
    )

    if (
        false_negative_cost <= 0
        or false_positive_cost <= 0
    ):
        raise ValueError(
            "Optimization costs must be > 0."
        )

    if minimum_recall is not None:

        minimum_recall = (
            _validate_probability(
                minimum_recall,
                "minimum_recall",
            )
        )

    if minimum_precision is not None:

        minimum_precision = (
            _validate_probability(
                minimum_precision,
                "minimum_precision",
            )
        )

    candidates = sorted(
        set(
            [
                0.0,
                1.0,
            ]
            +
            [
                float(value)
                for value in p
            ]
        )
    )

    feasible = []

    for threshold in candidates:

        result = evaluate_threshold(
            p.tolist(),
            y.astype(np.int64).tolist(),
            threshold=threshold,
            false_negative_cost=
                false_negative_cost,
            false_positive_cost=
                false_positive_cost,
        )

        if (
            minimum_recall
            is not None
            and result[
                "recall"
            ] < minimum_recall
        ):
            continue

        if (
            minimum_precision
            is not None
            and result[
                "precision"
            ] < minimum_precision
        ):
            continue

        feasible.append(
            result
        )

    if not feasible:
        raise ValueError(
            "No threshold satisfies supplied constraints."
        )

    # Deterministic tie-breaking only.
    # It is not an operational preference.
    best = min(
        feasible,
        key=lambda item: (
            item[
                "weighted_error_cost"
            ],
            item[
                "threshold"
            ],
        ),
    )

    return {
        **best,

        "candidate_count":
            len(
                candidates
            ),

        "feasible_candidate_count":
            len(
                feasible
            ),

        "selection_method":
            "MIN_WEIGHTED_FP_FN_COST",

        "minimum_recall_constraint":
            minimum_recall,

        "minimum_precision_constraint":
            minimum_precision,

        "operationally_approved":
            False,
    }


def optimize_band_thresholds(
    probabilities: Sequence[Any],
    labels: Sequence[Any],
    *,
    policies: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> dict[str, Any]:

    required = [
        "MONITOR",
        "WARNING",
        "ACTION",
    ]

    if list(
        sorted(
            policies.keys()
        )
    ) != list(
        sorted(
            required
        )
    ):
        raise ValueError(
            "Policies must contain exactly "
            "MONITOR, WARNING and ACTION."
        )

    results = {}

    for band in required:

        policy = policies[
            band
        ]

        results[
            band
        ] = optimize_threshold(
            probabilities,
            labels,
            false_negative_cost=
                policy[
                    "false_negative_cost"
                ],
            false_positive_cost=
                policy[
                    "false_positive_cost"
                ],
            minimum_recall=
                policy.get(
                    "minimum_recall"
                ),
            minimum_precision=
                policy.get(
                    "minimum_precision"
                ),
        )

    monitor = results[
        "MONITOR"
    ][
        "threshold"
    ]

    warning = results[
        "WARNING"
    ][
        "threshold"
    ]

    action = results[
        "ACTION"
    ][
        "threshold"
    ]

    ordered = (
        monitor
        <= warning
        <= action
    )

    return {
        "status":
            (
                "CANDIDATE_THRESHOLDS_ONLY"
                if ordered
                else
                "REVIEW_REQUIRED_NON_MONOTONIC_THRESHOLDS"
            ),

        "ordered":
            bool(
                ordered
            ),

        "thresholds":
            results,

        "tradeoff_documented":
            True,

        "false_negative_vs_unnecessary_intervention":
            "EXPLICIT_POLICY_COSTS_RECORDED",

        "operationally_approved":
            False,
    }


def build_candidate_calibration_artifact(
    *,
    candidate_version: str,
    model_version: str,
    feature_vector_version: str,
    calibrator: PlattCalibrator,
    calibration_comparison: Mapping[
        str,
        Any,
    ],
    threshold_candidates: Mapping[
        str,
        Any,
    ],
    calibration_dataset_id: str,
    threshold_dataset_id: str,
) -> dict[str, Any]:

    required_strings = {
        "candidate_version":
            candidate_version,

        "model_version":
            model_version,

        "feature_vector_version":
            feature_vector_version,

        "calibration_dataset_id":
            calibration_dataset_id,

        "threshold_dataset_id":
            threshold_dataset_id,
    }

    for name, value in required_strings.items():

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

    return {
        "schema_version":
            CALIBRATION_SCHEMA_VERSION,

        # Deliberately NOT VALIDATED.
        "status":
            CANDIDATE_STATUS,

        "version":
            candidate_version,

        "model_version":
            model_version,

        "feature_vector_version":
            feature_vector_version,

        "calibrator":
            calibrator.to_dict(),

        "calibration_metrics":
            dict(
                calibration_comparison
            ),

        "threshold_candidates":
            dict(
                threshold_candidates
            ),

        "data_provenance": {
            "calibration_dataset_id":
                calibration_dataset_id,

            "threshold_dataset_id":
                threshold_dataset_id,

            "independent_dataset_ids":
                (
                    calibration_dataset_id
                    != threshold_dataset_id
                ),
        },

        "scientific_guardrails": {
            "validated":
                False,

            "thresholds_operationally_approved":
                False,

            "action_threshold_operationally_approved":
                False,

            "synthetic_test_evidence_counts_as_real_validation":
                False,

            "physical_action_authorized":
                False,
        },
    }
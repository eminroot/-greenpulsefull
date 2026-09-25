from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import math
import numpy as np


MODEL_SCHEMA_VERSION = "greenpulse.sensor_only_baseline.v1"
EXPECTED_FEATURE_VECTOR_VERSION = "sensor_feature_vector_v1"

# The provenance/domain indicator "source_is_simulated" is deliberately
# excluded to prevent the model from learning simulation-vs-real shortcuts.
MODEL_FEATURE_NAMES = [
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


def _validate_binary_label(
    value: Any,
) -> int:

    if isinstance(
        value,
        bool,
    ):
        return int(
            value
        )

    if isinstance(
        value,
        (int, np.integer),
    ) and int(
        value
    ) in (0, 1):

        return int(
            value
        )

    raise ValueError(
        "stress_label must be binary 0/1."
    )


def _extract_model_vector(
    feature_record: Mapping[
        str,
        Any,
    ],
) -> np.ndarray:

    vector = feature_record.get(
        "feature_vector"
    )

    if not isinstance(
        vector,
        Mapping,
    ):
        raise ValueError(
            "Missing feature_vector."
        )

    if (
        feature_record.get(
            "feature_vector_version"
        )
        != EXPECTED_FEATURE_VECTOR_VERSION
    ):
        raise ValueError(
            "Unsupported sensor feature-vector version."
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
            "Feature names/raw_values missing."
        )

    if len(
        names
    ) != len(
        values
    ):
        raise ValueError(
            "Feature name/value length mismatch."
        )

    mapping = dict(
        zip(
            names,
            values,
        )
    )

    missing = [
        name
        for name in MODEL_FEATURE_NAMES
        if name not in mapping
    ]

    if missing:
        raise ValueError(
            "Required sensor model features missing: "
            + ", ".join(
                missing
            )
        )

    values = np.asarray(
        [
            _finite_float(
                mapping[
                    name
                ],
                name,
            )
            for name in MODEL_FEATURE_NAMES
        ],
        dtype=np.float64,
    )

    if values.shape != (
        len(
            MODEL_FEATURE_NAMES
        ),
    ):
        raise RuntimeError(
            "Unexpected model-vector shape."
        )

    return values


def prepare_labeled_dataset(
    records: Sequence[
        Mapping[str, Any]
    ],
) -> tuple[
    np.ndarray,
    np.ndarray,
]:

    if len(
        records
    ) < 2:
        raise ValueError(
            "At least two labeled records are required."
        )

    rows = []

    labels = []

    for record in records:

        if not isinstance(
            record,
            Mapping,
        ):
            raise TypeError(
                "Each training record must be a mapping."
            )

        features = record.get(
            "sensor_features"
        )

        if not isinstance(
            features,
            Mapping,
        ):
            raise ValueError(
                "Record missing sensor_features."
            )

        rows.append(
            _extract_model_vector(
                features
            )
        )

        labels.append(
            _validate_binary_label(
                record.get(
                    "stress_label"
                )
            )
        )

    X = np.vstack(
        rows
    ).astype(
        np.float64
    )

    y = np.asarray(
        labels,
        dtype=np.float64,
    )

    if len(
        np.unique(
            y
        )
    ) < 2:
        raise ValueError(
            "Training data must contain both binary classes."
        )

    return (
        X,
        y,
    )


def _canonical_training_order(
    X: np.ndarray,
    y: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
]:

    # Deterministic row ordering prevents input-order differences
    # from changing floating-point accumulation order.
    combined = np.column_stack(
        [
            X,
            y,
        ]
    )

    order = sorted(
        range(
            combined.shape[0]
        ),
        key=lambda i: tuple(
            float(v)
            for v in combined[
                i
            ]
        ),
    )

    order = np.asarray(
        order,
        dtype=np.int64,
    )

    return (
        X[
            order
        ],
        y[
            order
        ],
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
            + np.exp(
                -clipped
            )
        )
    )


@dataclass
class SensorOnlyBaselineModel:

    feature_names: list[str]

    scaler_mean: list[float]

    scaler_scale: list[float]

    weights: list[float]

    bias: float

    decision_threshold: float

    training_iterations: int

    learning_rate: float

    l2_strength: float

    model_schema_version: str = MODEL_SCHEMA_VERSION

    feature_vector_version: str = EXPECTED_FEATURE_VECTOR_VERSION


    def _transform(
        self,
        X: np.ndarray,
    ) -> np.ndarray:

        X = np.asarray(
            X,
            dtype=np.float64,
        )

        mean = np.asarray(
            self.scaler_mean,
            dtype=np.float64,
        )

        scale = np.asarray(
            self.scaler_scale,
            dtype=np.float64,
        )

        if (
            X.ndim != 2
            or X.shape[1] != len(
                self.feature_names
            )
        ):
            raise ValueError(
                "Input feature shape mismatch."
            )

        return (
            X
            - mean
        ) / scale


    def predict_proba_matrix(
        self,
        X: np.ndarray,
    ) -> np.ndarray:

        transformed = self._transform(
            X
        )

        weights = np.asarray(
            self.weights,
            dtype=np.float64,
        )

        logits = (
            transformed
            @ weights
            + float(
                self.bias
            )
        )

        return _sigmoid(
            logits
        )


    def predict_matrix(
        self,
        X: np.ndarray,
    ) -> np.ndarray:

        probabilities = (
            self.predict_proba_matrix(
                X
            )
        )

        return (
            probabilities
            >= float(
                self.decision_threshold
            )
        ).astype(
            np.int64
        )


    def predict_feature_record(
        self,
        sensor_features: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:

        row = _extract_model_vector(
            sensor_features
        ).reshape(
            1,
            -1,
        )

        probability = float(
            self.predict_proba_matrix(
                row
            )[0]
        )

        prediction = int(
            probability
            >= self.decision_threshold
        )

        return {
            "model_schema_version":
                self.model_schema_version,

            "feature_vector_version":
                self.feature_vector_version,

            "stress_probability":
                probability,

            "predicted_label":
                prediction,

            "decision_threshold":
                float(
                    self.decision_threshold
                ),

            "scientific_guardrails": {
                "probability_is_real_world_calibrated":
                    False,

                "physical_action_authorized":
                    False,
            },
        }


    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "model_schema_version":
                self.model_schema_version,

            "feature_vector_version":
                self.feature_vector_version,

            "model_type":
                "NUMPY_LOGISTIC_REGRESSION",

            "feature_names":
                list(
                    self.feature_names
                ),

            "scaler": {
                "mean":
                    list(
                        self.scaler_mean
                    ),

                "scale":
                    list(
                        self.scaler_scale
                    ),

                "fit_scope":
                    "TRAIN_ONLY",
            },

            "parameters": {
                "weights":
                    list(
                        self.weights
                    ),

                "bias":
                    float(
                        self.bias
                    ),

                "decision_threshold":
                    float(
                        self.decision_threshold
                    ),
            },

            "training": {
                "iterations":
                    int(
                        self.training_iterations
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

            "scientific_guardrails": {
                "source_is_simulated_feature_excluded":
                    True,

                "train_validation_split_created_inside_model":
                    False,

                "real_sensor_performance_validated":
                    False,

                "physical_action_authorized":
                    False,
            },
        }


    @classmethod
    def from_dict(
        cls,
        payload: Mapping[
            str,
            Any,
        ],
    ) -> "SensorOnlyBaselineModel":

        if (
            payload.get(
                "model_schema_version"
            )
            != MODEL_SCHEMA_VERSION
        ):
            raise ValueError(
                "Unsupported sensor baseline model schema."
            )

        if (
            payload.get(
                "feature_vector_version"
            )
            != EXPECTED_FEATURE_VECTOR_VERSION
        ):
            raise ValueError(
                "Feature-vector version mismatch."
            )

        feature_names = list(
            payload[
                "feature_names"
            ]
        )

        if feature_names != MODEL_FEATURE_NAMES:
            raise ValueError(
                "Model feature schema mismatch."
            )

        scaler = payload[
            "scaler"
        ]

        parameters = payload[
            "parameters"
        ]

        training = payload[
            "training"
        ]

        return cls(
            feature_names=
                feature_names,

            scaler_mean=[
                _finite_float(
                    value,
                    "scaler_mean",
                )
                for value in scaler[
                    "mean"
                ]
            ],

            scaler_scale=[
                _finite_float(
                    value,
                    "scaler_scale",
                )
                for value in scaler[
                    "scale"
                ]
            ],

            weights=[
                _finite_float(
                    value,
                    "weight",
                )
                for value in parameters[
                    "weights"
                ]
            ],

            bias=
                _finite_float(
                    parameters[
                        "bias"
                    ],
                    "bias",
                ),

            decision_threshold=
                _finite_float(
                    parameters[
                        "decision_threshold"
                    ],
                    "decision_threshold",
                ),

            training_iterations=
                int(
                    training[
                        "iterations"
                    ]
                ),

            learning_rate=
                _finite_float(
                    training[
                        "learning_rate"
                    ],
                    "learning_rate",
                ),

            l2_strength=
                _finite_float(
                    training[
                        "l2_strength"
                    ],
                    "l2_strength",
                ),
        )


def train_sensor_only_baseline(
    training_records: Sequence[
        Mapping[str, Any]
    ],
    *,
    iterations: int = 2000,
    learning_rate: float = 0.05,
    l2_strength: float = 0.001,
    decision_threshold: float = 0.5,
) -> SensorOnlyBaselineModel:

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

    decision_threshold = _finite_float(
        decision_threshold,
        "decision_threshold",
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

    if not (
        0.0
        < decision_threshold
        < 1.0
    ):
        raise ValueError(
            "decision_threshold must be in (0, 1)."
        )

    X, y = prepare_labeled_dataset(
        training_records
    )

    X, y = _canonical_training_order(
        X,
        y,
    )

    scaler_mean = np.mean(
        X,
        axis=0,
    )

    scaler_scale = np.std(
        X,
        axis=0,
    )

    scaler_scale = np.where(
        scaler_scale < 1e-12,
        1.0,
        scaler_scale,
    )

    X_scaled = (
        X
        - scaler_mean
    ) / scaler_scale

    weights = np.zeros(
        X_scaled.shape[1],
        dtype=np.float64,
    )

    bias = 0.0

    n = float(
        X_scaled.shape[0]
    )

    for _ in range(
        iterations
    ):

        logits = (
            X_scaled
            @ weights
            + bias
        )

        probability = _sigmoid(
            logits
        )

        error = (
            probability
            - y
        )

        gradient_w = (
            X_scaled.T
            @ error
        ) / n

        gradient_w += (
            l2_strength
            * weights
        )

        gradient_b = float(
            math.fsum(
                float(v)
                for v in error
            ) / n
        )

        weights -= (
            learning_rate
            * gradient_w
        )

        bias -= (
            learning_rate
            * gradient_b
        )

    return SensorOnlyBaselineModel(
        feature_names=
            list(
                MODEL_FEATURE_NAMES
            ),

        scaler_mean=[
            float(v)
            for v in scaler_mean
        ],

        scaler_scale=[
            float(v)
            for v in scaler_scale
        ],

        weights=[
            float(v)
            for v in weights
        ],

        bias=
            float(
                bias
            ),

        decision_threshold=
            float(
                decision_threshold
            ),

        training_iterations=
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


def evaluate_sensor_only_baseline(
    model: SensorOnlyBaselineModel,
    evaluation_records: Sequence[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    X, y_float = prepare_labeled_dataset(
        evaluation_records
    )

    y = y_float.astype(
        np.int64
    )

    predictions = model.predict_matrix(
        X
    )

    probabilities = (
        model.predict_proba_matrix(
            X
        )
    )

    tp = int(
        np.sum(
            (y == 1)
            & (predictions == 1)
        )
    )

    tn = int(
        np.sum(
            (y == 0)
            & (predictions == 0)
        )
    )

    fp = int(
        np.sum(
            (y == 0)
            & (predictions == 1)
        )
    )

    fn = int(
        np.sum(
            (y == 1)
            & (predictions == 0)
        )
    )

    total = int(
        len(
            y
        )
    )

    accuracy = (
        (tp + tn) / total
        if total
        else 0.0
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

    f1 = (
        2.0
        * precision
        * recall
        / (
            precision
            + recall
        )
        if (
            precision
            + recall
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

    return {
        "model_schema_version":
            model.model_schema_version,

        "feature_vector_version":
            model.feature_vector_version,

        "sample_count":
            total,

        "metrics": {
            "accuracy":
                float(
                    accuracy
                ),

            "precision":
                float(
                    precision
                ),

            "recall":
                float(
                    recall
                ),

            "f1":
                float(
                    f1
                ),

            "false_positive_rate":
                float(
                    false_positive_rate
                ),

            "false_negative_rate":
                float(
                    false_negative_rate
                ),
        },

        "confusion": {
            "true_positive":
                tp,

            "true_negative":
                tn,

            "false_positive":
                fp,

            "false_negative":
                fn,
        },

        "probabilities": [
            float(v)
            for v in probabilities
        ],

        "scientific_guardrails": {
            "evaluation_is_real_sensor_validation":
                False,

            "metrics_may_only_be_claimed_for_the_supplied_dataset":
                True,

            "physical_action_authorized":
                False,
        },
    }
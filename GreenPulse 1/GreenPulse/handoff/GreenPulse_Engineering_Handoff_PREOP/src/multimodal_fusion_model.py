from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import math
import numpy as np

from src.feature_fusion import (
    FEATURE_VECTOR_VERSION as EXPECTED_FUSION_VECTOR_VERSION,
    FUSION_FEATURE_NAMES,
)


MODEL_SCHEMA_VERSION = (
    "greenpulse.multimodal_stress_fusion_model.v1"
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


def _binary_label(
    value: Any,
) -> int:

    if isinstance(
        value,
        bool,
    ):
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
        "stress_label must be binary 0/1."
    )


def extract_fusion_vector(
    fused_features: Mapping[
        str,
        Any,
    ],
) -> np.ndarray:

    if (
        fused_features.get(
            "feature_vector_version"
        )
        != EXPECTED_FUSION_VECTOR_VERSION
    ):
        raise ValueError(
            "Unsupported multimodal feature-vector version."
        )

    vector = fused_features.get(
        "feature_vector"
    )

    if not isinstance(
        vector,
        Mapping,
    ):
        raise ValueError(
            "Missing multimodal feature_vector."
        )

    names = vector.get(
        "names"
    )

    values = vector.get(
        "values"
    )

    if not isinstance(
        names,
        list,
    ) or not isinstance(
        values,
        list,
    ):
        raise ValueError(
            "Fusion feature names/values missing."
        )

    if names != list(
        FUSION_FEATURE_NAMES
    ):
        raise ValueError(
            "Fusion feature schema/order mismatch."
        )

    if len(values) != len(
        FUSION_FEATURE_NAMES
    ):
        raise ValueError(
            "Fusion feature-vector length mismatch."
        )

    result = np.asarray(
        [
            _finite_float(
                value,
                name,
            )
            for name, value
            in zip(
                names,
                values,
            )
        ],
        dtype=np.float64,
    )

    if not np.all(
        np.isfinite(result)
    ):
        raise ValueError(
            "Fusion vector contains non-finite values."
        )

    return result


def prepare_labeled_dataset(
    records: Sequence[
        Mapping[str, Any]
    ],
    *,
    require_both_classes: bool,
) -> tuple[
    np.ndarray,
    np.ndarray,
]:

    if len(records) < 1:
        raise ValueError(
            "At least one labeled record is required."
        )

    rows = []
    labels = []

    for record in records:

        if not isinstance(
            record,
            Mapping,
        ):
            raise TypeError(
                "Each record must be a mapping."
            )

        fused = record.get(
            "fused_features"
        )

        if not isinstance(
            fused,
            Mapping,
        ):
            raise ValueError(
                "Record missing fused_features."
            )

        rows.append(
            extract_fusion_vector(
                fused
            )
        )

        labels.append(
            _binary_label(
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

    if (
        require_both_classes
        and len(
            np.unique(y)
        ) < 2
    ):
        raise ValueError(
            "Training data must contain both classes."
        )

    return (
        X,
        y,
    )


def _canonical_order(
    X: np.ndarray,
    y: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
]:

    combined = np.column_stack(
        [
            X,
            y,
        ]
    )

    indices = sorted(
        range(
            combined.shape[0]
        ),
        key=lambda index: tuple(
            float(value)
            for value
            in combined[index]
        ),
    )

    order = np.asarray(
        indices,
        dtype=np.int64,
    )

    return (
        X[order],
        y[order],
    )


def _sigmoid(
    values: np.ndarray,
) -> np.ndarray:

    values = np.clip(
        values,
        -35.0,
        35.0,
    )

    return (
        1.0
        /
        (
            1.0
            + np.exp(-values)
        )
    )


@dataclass
class MultimodalFusionModel:

    feature_names: list[str]

    scaler_mean: list[float]

    scaler_scale: list[float]

    weights: list[float]

    bias: float

    decision_threshold: float

    training_iterations: int

    learning_rate: float

    l2_strength: float

    model_schema_version: str = (
        MODEL_SCHEMA_VERSION
    )

    feature_vector_version: str = (
        EXPECTED_FUSION_VECTOR_VERSION
    )


    def _transform(
        self,
        X: np.ndarray,
    ) -> np.ndarray:

        X = np.asarray(
            X,
            dtype=np.float64,
        )

        if (
            X.ndim != 2
            or X.shape[1]
            != len(
                self.feature_names
            )
        ):
            raise ValueError(
                "Fusion model input shape mismatch."
            )

        mean = np.asarray(
            self.scaler_mean,
            dtype=np.float64,
        )

        scale = np.asarray(
            self.scaler_scale,
            dtype=np.float64,
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

        probability = (
            self.predict_proba_matrix(
                X
            )
        )

        return (
            probability
            >= self.decision_threshold
        ).astype(
            np.int64
        )


    def predict_record(
        self,
        fused_features: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:

        vector = extract_fusion_vector(
            fused_features
        ).reshape(
            1,
            -1,
        )

        probability = float(
            self.predict_proba_matrix(
                vector
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

            "positive_class_probability":
                probability,

            "predicted_label":
                prediction,

            "decision_threshold":
                float(
                    self.decision_threshold
                ),

            "operational_water_stress_probability":
                None,

            "scientific_guardrails": {
                "probability_is_real_world_calibrated":
                    False,

                "multimodal_superiority_established":
                    False,

                "operational_risk_score_authorized":
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
                "internal_train_test_split":
                    False,

                "scaler_fit_scope":
                    "TRAIN_ONLY",

                "real_multimodal_performance_validated":
                    False,

                "multimodal_benefit_established":
                    False,

                "operational_water_stress_model":
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
    ) -> "MultimodalFusionModel":

        if (
            payload.get(
                "model_schema_version"
            )
            != MODEL_SCHEMA_VERSION
        ):
            raise ValueError(
                "Unsupported fusion model schema."
            )

        if (
            payload.get(
                "feature_vector_version"
            )
            != EXPECTED_FUSION_VECTOR_VERSION
        ):
            raise ValueError(
                "Fusion feature-vector version mismatch."
            )

        feature_names = list(
            payload[
                "feature_names"
            ]
        )

        if feature_names != list(
            FUSION_FEATURE_NAMES
        ):
            raise ValueError(
                "Fusion model feature schema mismatch."
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
                    "scaler mean",
                )
                for value in scaler[
                    "mean"
                ]
            ],

            scaler_scale=[
                _finite_float(
                    value,
                    "scaler scale",
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
                    "decision threshold",
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
                    "learning rate",
                ),

            l2_strength=
                _finite_float(
                    training[
                        "l2_strength"
                    ],
                    "l2 strength",
                ),
        )


def train_multimodal_fusion_model(
    training_records: Sequence[
        Mapping[str, Any]
    ],
    *,
    iterations: int = 2000,
    learning_rate: float = 0.05,
    l2_strength: float = 0.001,
    decision_threshold: float = 0.5,
) -> MultimodalFusionModel:

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
        training_records,
        require_both_classes=True,
    )

    X, y = _canonical_order(
        X,
        y,
    )

    mean = np.mean(
        X,
        axis=0,
    )

    scale = np.std(
        X,
        axis=0,
    )

    scale = np.where(
        scale < 1e-12,
        1.0,
        scale,
    )

    X_scaled = (
        X
        - mean
    ) / scale

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
                float(value)
                for value in error
            )
            / n
        )

        weights -= (
            learning_rate
            * gradient_w
        )

        bias -= (
            learning_rate
            * gradient_b
        )

    return MultimodalFusionModel(
        feature_names=
            list(
                FUSION_FEATURE_NAMES
            ),

        scaler_mean=[
            float(value)
            for value in mean
        ],

        scaler_scale=[
            float(value)
            for value in scale
        ],

        weights=[
            float(value)
            for value in weights
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


def evaluate_multimodal_fusion_model(
    model: MultimodalFusionModel,
    evaluation_records: Sequence[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    X, y_float = prepare_labeled_dataset(
        evaluation_records,
        require_both_classes=False,
    )

    y = y_float.astype(
        np.int64
    )

    probabilities = (
        model.predict_proba_matrix(
            X
        )
    )

    predictions = (
        probabilities
        >= model.decision_threshold
    ).astype(
        np.int64
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
        len(y)
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
            float(value)
            for value in probabilities
        ],

        "scientific_guardrails": {
            "metrics_are_real_multimodal_validation":
                False,

            "multimodal_superiority_established":
                False,

            "metrics_only_describe_supplied_dataset":
                True,

            "operational_water_stress_probability":
                False,

            "physical_action_authorized":
                False,
        },
    }
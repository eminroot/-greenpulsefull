from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

import math
import numpy as np


MODEL_SCHEMA_VERSION = "greenpulse.vision_only_baseline.v1"

EXPECTED_VISUAL_FEATURE_VECTOR_VERSION = (
    "visual_feature_vector_v1"
)

EXPECTED_PLANT_DELTA_SCHEMA_VERSION = (
    "greenpulse.plant_delta.v1"
)


VISUAL_FEATURE_NAMES = [
    "visual_confidence",
    "affected_leaf_area_ratio",
    "affected_leaf_area_available",

    "rgb_r_mean",
    "rgb_g_mean",
    "rgb_b_mean",

    "rgb_r_std",
    "rgb_g_std",
    "rgb_b_std",

    "hsv_h_mean",
    "hsv_s_mean",
    "hsv_v_mean",

    "hsv_h_std",
    "hsv_s_std",
    "hsv_v_std",

    "gray_mean",
    "gray_std",

    "gradient_mean",
    "gradient_std",
    "edge_density",
    "laplacian_energy",

    "relative_visual_change",
    "relative_visual_change_available",
]


PLANT_DELTA_FEATURE_NAMES = [
    "plant_color_delta",
    "plant_texture_delta",

    "plant_confidence_delta_absolute",
    "plant_confidence_delta_signed",

    "plant_affected_area_delta_absolute",
    "plant_affected_area_delta_signed",
    "plant_affected_area_delta_available",

    "plant_delta_available",
]


MODEL_FEATURE_NAMES = (
    VISUAL_FEATURE_NAMES
    + PLANT_DELTA_FEATURE_NAMES
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

    if (
        isinstance(
            value,
            (int, np.integer),
        )
        and int(
            value
        )
        in (0, 1)
    ):
        return int(
            value
        )

    raise ValueError(
        "stress_label must be binary 0/1."
    )


def _extract_visual_vector(
    visual_features: Mapping[
        str,
        Any,
    ],
) -> list[float]:

    if (
        visual_features.get(
            "feature_vector_version"
        )
        != EXPECTED_VISUAL_FEATURE_VECTOR_VERSION
    ):
        raise ValueError(
            "Unsupported visual feature-vector version."
        )

    vector = visual_features.get(
        "feature_vector"
    )

    if not isinstance(
        vector,
        Mapping,
    ):
        raise ValueError(
            "Missing visual feature_vector."
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
            "Visual feature names/values missing."
        )

    if len(
        names
    ) != len(
        values
    ):
        raise ValueError(
            "Visual feature name/value length mismatch."
        )

    mapping = dict(
        zip(
            names,
            values,
        )
    )

    missing = [
        name
        for name in VISUAL_FEATURE_NAMES
        if name not in mapping
    ]

    if missing:
        raise ValueError(
            "Required visual features missing: "
            + ", ".join(
                missing
            )
        )

    return [
        _finite_float(
            mapping[
                name
            ],
            name,
        )
        for name in VISUAL_FEATURE_NAMES
    ]


def _extract_plant_delta_vector(
    plant_delta: Optional[
        Mapping[str, Any]
    ],
) -> list[float]:

    if plant_delta is None:

        return [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]

    if (
        plant_delta.get(
            "schema_version"
        )
        != EXPECTED_PLANT_DELTA_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported plant-delta schema."
        )

    color = plant_delta.get(
        "color_delta"
    )

    texture = plant_delta.get(
        "texture_delta"
    )

    confidence = plant_delta.get(
        "confidence_delta"
    )

    affected = plant_delta.get(
        "affected_area_delta"
    )

    if not all(
        isinstance(
            item,
            Mapping,
        )
        for item in (
            color,
            texture,
            confidence,
            affected,
        )
    ):
        raise ValueError(
            "Plant delta record is incomplete."
        )

    affected_available = bool(
        affected.get(
            "available"
        )
    )

    affected_absolute = (
        _finite_float(
            affected[
                "absolute"
            ],
            "affected_area_delta.absolute",
        )
        if (
            affected_available
            and affected.get(
                "absolute"
            )
            is not None
        )
        else 0.0
    )

    affected_signed = (
        _finite_float(
            affected[
                "signed"
            ],
            "affected_area_delta.signed",
        )
        if (
            affected_available
            and affected.get(
                "signed"
            )
            is not None
        )
        else 0.0
    )

    return [
        _finite_float(
            color[
                "score"
            ],
            "color_delta.score",
        ),

        _finite_float(
            texture[
                "score"
            ],
            "texture_delta.score",
        ),

        _finite_float(
            confidence[
                "absolute"
            ],
            "confidence_delta.absolute",
        ),

        _finite_float(
            confidence[
                "signed"
            ],
            "confidence_delta.signed",
        ),

        affected_absolute,

        affected_signed,

        float(
            affected_available
        ),

        1.0,
    ]


def extract_model_vector(
    visual_features: Mapping[
        str,
        Any,
    ],
    plant_delta: Optional[
        Mapping[str, Any]
    ] = None,
) -> np.ndarray:

    visual_values = _extract_visual_vector(
        visual_features
    )

    delta_values = _extract_plant_delta_vector(
        plant_delta
    )

    values = np.asarray(
        visual_values
        + delta_values,
        dtype=np.float64,
    )

    if values.shape != (
        len(
            MODEL_FEATURE_NAMES
        ),
    ):
        raise RuntimeError(
            "Vision-only model-vector schema mismatch."
        )

    if not np.all(
        np.isfinite(
            values
        )
    ):
        raise ValueError(
            "Vision-only model vector contains "
            "non-finite values."
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
                "Each record must be a mapping."
            )

        visual_features = record.get(
            "visual_features"
        )

        if not isinstance(
            visual_features,
            Mapping,
        ):
            raise ValueError(
                "Record missing visual_features."
            )

        rows.append(
            extract_model_vector(
                visual_features,
                record.get(
                    "plant_delta"
                ),
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
            "Training/evaluation data must "
            "contain both binary classes."
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
        key=lambda index: tuple(
            float(value)
            for value in combined[
                index
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
class VisionOnlyBaselineModel:

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

    visual_feature_vector_version: str = (
        EXPECTED_VISUAL_FEATURE_VECTOR_VERSION
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
                "Input feature shape mismatch."
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


    def predict_record(
        self,
        visual_features: Mapping[
            str,
            Any,
        ],
        plant_delta: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> dict[str, Any]:

        vector = extract_model_vector(
            visual_features,
            plant_delta,
        ).reshape(
            1,
            -1,
        )

        probability = float(
            self.predict_proba_matrix(
                vector
            )[0]
        )

        predicted_label = int(
            probability
            >= self.decision_threshold
        )

        return {
            "model_schema_version":
                self.model_schema_version,

            "visual_feature_vector_version":
                self.visual_feature_vector_version,

            "stress_probability":
                probability,

            "predicted_label":
                predicted_label,

            "decision_threshold":
                float(
                    self.decision_threshold
                ),

            "scientific_guardrails": {
                "probability_is_water_stress_probability":
                    False,

                "probability_is_real_world_calibrated":
                    False,

                "disease_classification_is_water_stress":
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

            "visual_feature_vector_version":
                self.visual_feature_vector_version,

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
                "disease_class_name_used_as_feature":
                    False,

                "gradcam_used_as_model_feature":
                    False,

                "scaler_fit_scope":
                    "TRAIN_ONLY",

                "internal_train_test_split":
                    False,

                "real_visual_stress_performance_validated":
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
    ) -> "VisionOnlyBaselineModel":

        if (
            payload.get(
                "model_schema_version"
            )
            != MODEL_SCHEMA_VERSION
        ):
            raise ValueError(
                "Unsupported vision baseline model schema."
            )

        if (
            payload.get(
                "visual_feature_vector_version"
            )
            != EXPECTED_VISUAL_FEATURE_VECTOR_VERSION
        ):
            raise ValueError(
                "Visual feature-vector version mismatch."
            )

        feature_names = list(
            payload[
                "feature_names"
            ]
        )

        if feature_names != MODEL_FEATURE_NAMES:
            raise ValueError(
                "Vision baseline feature schema mismatch."
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


def train_vision_only_baseline(
    training_records: Sequence[
        Mapping[str, Any]
    ],
    *,
    iterations: int = 2000,
    learning_rate: float = 0.05,
    l2_strength: float = 0.001,
    decision_threshold: float = 0.5,
) -> VisionOnlyBaselineModel:

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

    sample_count = float(
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
        ) / sample_count

        gradient_w += (
            l2_strength
            * weights
        )

        gradient_b = float(
            math.fsum(
                float(value)
                for value in error
            )
            / sample_count
        )

        weights -= (
            learning_rate
            * gradient_w
        )

        bias -= (
            learning_rate
            * gradient_b
        )

    return VisionOnlyBaselineModel(
        feature_names=
            list(
                MODEL_FEATURE_NAMES
            ),

        scaler_mean=[
            float(value)
            for value in scaler_mean
        ],

        scaler_scale=[
            float(value)
            for value in scaler_scale
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


def evaluate_vision_only_baseline(
    model: VisionOnlyBaselineModel,
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
            "evaluation_is_real_visual_stress_validation":
                False,

            "metrics_only_describe_supplied_dataset":
                True,

            "disease_classification_is_water_stress":
                False,

            "physical_action_authorized":
                False,
        },
    }
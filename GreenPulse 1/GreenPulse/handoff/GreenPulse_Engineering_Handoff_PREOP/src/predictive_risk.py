from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

import math
import numpy as np


MODEL_SCHEMA_VERSION = (
    "greenpulse.predictive_plant_risk.v1"
)

EXPECTED_TEMPORAL_SCHEMA_VERSION = (
    "greenpulse.temporal_intelligence.v1"
)

EXPECTED_TEMPORAL_VECTOR_VERSION = (
    "temporal_feature_vector_v1"
)

EXPECTED_PLANT_DELTA_SCHEMA_VERSION = (
    "greenpulse.plant_delta.v1"
)


MODEL_FEATURE_NAMES = [
    "current_risk_score",

    "risk_trend_code",
    "risk_velocity",
    "risk_acceleration",

    "soil_trend_velocity",
    "soil_trend_available",

    "temperature_trend_velocity",
    "temperature_trend_available",

    "humidity_trend_velocity",
    "humidity_trend_available",

    "visual_color_delta",
    "visual_texture_delta",
    "visual_confidence_delta_signed",

    "visual_affected_area_delta_signed",
    "visual_affected_area_delta_available",

    "visual_delta_available",
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


def _risk_score(
    value: Any,
    name: str,
) -> float:

    result = _finite_float(
        value,
        name,
    )

    if not (
        0.0
        <= result
        <= 100.0
    ):
        raise ValueError(
            f"{name} must be in [0, 100]."
        )

    return result


def _validate_horizon(
    value: Any,
) -> float:

    horizon = _finite_float(
        value,
        "horizon_hours",
    )

    if horizon <= 0.0:
        raise ValueError(
            "horizon_hours must be > 0."
        )

    return horizon


def _extract_temporal_core(
    temporal_features: Mapping[
        str,
        Any,
    ],
) -> list[float]:

    if not isinstance(
        temporal_features,
        Mapping,
    ):
        raise TypeError(
            "temporal_features must be a mapping."
        )

    if (
        temporal_features.get(
            "schema_version"
        )
        != EXPECTED_TEMPORAL_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported temporal schema."
        )

    if (
        temporal_features.get(
            "feature_vector_version"
        )
        != EXPECTED_TEMPORAL_VECTOR_VERSION
    ):
        raise ValueError(
            "Unsupported temporal feature-vector version."
        )

    if (
        temporal_features.get(
            "status"
        )
        != "TEMPORAL_FEATURES_AVAILABLE"
    ):
        raise ValueError(
            "Forecast requires sufficient temporal history."
        )

    vector = temporal_features.get(
        "feature_vector"
    )

    if not isinstance(
        vector,
        Mapping,
    ):
        raise ValueError(
            "Temporal feature_vector missing."
        )

    names = vector.get(
        "names"
    )

    values = vector.get(
        "values"
    )

    expected_names = [
        "risk_trend_code",
        "risk_velocity",
        "risk_acceleration",
        "temporal_consistency_code",
    ]

    if names != expected_names:
        raise ValueError(
            "Temporal feature schema/order mismatch."
        )

    if (
        not isinstance(
            values,
            list,
        )
        or len(values) != 4
    ):
        raise ValueError(
            "Temporal feature values invalid."
        )

    return [
        _finite_float(
            values[0],
            "risk_trend_code",
        ),
        _finite_float(
            values[1],
            "risk_velocity",
        ),
        _finite_float(
            values[2],
            "risk_acceleration",
        ),
    ]


def _sensor_trend_pair(
    temporal_features: Mapping[
        str,
        Any,
    ],
    field: str,
) -> tuple[float, float]:

    trends = temporal_features.get(
        "sensor_trends"
    )

    if not isinstance(
        trends,
        Mapping,
    ):
        return (
            0.0,
            0.0,
        )

    item = trends.get(
        field
    )

    if not isinstance(
        item,
        Mapping,
    ):
        return (
            0.0,
            0.0,
        )

    if item.get(
        "available"
    ) is not True:

        return (
            0.0,
            0.0,
        )

    velocity = _finite_float(
        item.get(
            "velocity"
        ),
        f"{field}.velocity",
    )

    return (
        velocity,
        1.0,
    )


def _extract_visual_delta(
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
            "Plant-delta record is incomplete."
        )

    affected_available = bool(
        affected.get(
            "available"
        )
    )

    affected_signed = (
        _finite_float(
            affected.get(
                "signed"
            ),
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
            color.get(
                "score"
            ),
            "color_delta.score",
        ),

        _finite_float(
            texture.get(
                "score"
            ),
            "texture_delta.score",
        ),

        _finite_float(
            confidence.get(
                "signed"
            ),
            "confidence_delta.signed",
        ),

        affected_signed,

        float(
            affected_available
        ),

        1.0,
    ]


def extract_forecast_features(
    *,
    current_risk_score: Any,
    temporal_features: Mapping[
        str,
        Any,
    ],
    plant_delta: Optional[
        Mapping[str, Any]
    ] = None,
) -> np.ndarray:

    current_risk = _risk_score(
        current_risk_score,
        "current_risk_score",
    )

    temporal = _extract_temporal_core(
        temporal_features
    )

    soil = _sensor_trend_pair(
        temporal_features,
        "soil_moisture_pct",
    )

    temperature = _sensor_trend_pair(
        temporal_features,
        "temperature_c",
    )

    humidity = _sensor_trend_pair(
        temporal_features,
        "humidity_pct",
    )

    visual = _extract_visual_delta(
        plant_delta
    )

    values = np.asarray(
        [
            current_risk,
            *temporal,
            *soil,
            *temperature,
            *humidity,
            *visual,
        ],
        dtype=np.float64,
    )

    if values.shape != (
        len(
            MODEL_FEATURE_NAMES
        ),
    ):
        raise RuntimeError(
            "Forecast feature schema mismatch."
        )

    if not np.all(
        np.isfinite(
            values
        )
    ):
        raise ValueError(
            "Forecast features contain non-finite values."
        )

    return values


def prepare_training_dataset(
    records: Sequence[
        Mapping[str, Any]
    ],
    *,
    horizon_hours: float,
) -> tuple[
    np.ndarray,
    np.ndarray,
]:

    horizon = _validate_horizon(
        horizon_hours
    )

    if len(records) < 2:

        raise ValueError(
            "At least two forecast training records are required."
        )

    rows = []
    targets = []

    for record in records:

        if not isinstance(
            record,
            Mapping,
        ):

            raise TypeError(
                "Each training record must be a mapping."
            )

        record_horizon = _validate_horizon(
            record.get(
                "horizon_hours"
            )
        )

        if not math.isclose(
            record_horizon,
            horizon,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):

            raise ValueError(
                "Mixed forecast horizons are not allowed "
                "inside one model."
            )

        rows.append(
            extract_forecast_features(
                current_risk_score=
                    record.get(
                        "current_risk_score"
                    ),

                temporal_features=
                    record.get(
                        "temporal_features"
                    ),

                plant_delta=
                    record.get(
                        "plant_delta"
                    ),
            )
        )

        targets.append(
            _risk_score(
                record.get(
                    "future_risk_score"
                ),
                "future_risk_score",
            )
        )

    return (
        np.vstack(
            rows
        ).astype(
            np.float64
        ),

        np.asarray(
            targets,
            dtype=np.float64,
        ),
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


@dataclass
class PredictiveRiskModel:

    model_version: str

    horizon_hours: float

    feature_names: list[str]

    scaler_mean: list[float]

    scaler_scale: list[float]

    coefficients: list[float]

    intercept: float

    l2_strength: float

    training_residual_std: float

    model_schema_version: str = (
        MODEL_SCHEMA_VERSION
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
                "Forecast model input shape mismatch."
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


    def predict_matrix(
        self,
        X: np.ndarray,
    ) -> np.ndarray:

        transformed = self._transform(
            X
        )

        coefficients = np.asarray(
            self.coefficients,
            dtype=np.float64,
        )

        raw = (
            transformed
            @ coefficients
            + float(
                self.intercept
            )
        )

        return np.clip(
            raw,
            0.0,
            100.0,
        )


    def predict_record(
        self,
        *,
        current_risk_score: Any,
        temporal_features: Mapping[
            str,
            Any,
        ],
        plant_delta: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> dict[str, Any]:

        current_risk = _risk_score(
            current_risk_score,
            "current_risk_score",
        )

        try:

            vector = extract_forecast_features(
                current_risk_score=
                    current_risk,

                temporal_features=
                    temporal_features,

                plant_delta=
                    plant_delta,
            )

        except ValueError as exc:

            if (
                "sufficient temporal history"
                in str(exc)
            ):

                return {
                    "status":
                        "BLOCKED_INSUFFICIENT_TEMPORAL_HISTORY",

                    "future_risk":
                        None,

                    "naive_future_risk":
                        current_risk,

                    "horizon_hours":
                        float(
                            self.horizon_hours
                        ),

                    "uncertainty":
                        None,

                    "model_version":
                        self.model_version,

                    "physical_action_authorized":
                        False,
                }

            raise


        future_risk = float(
            self.predict_matrix(
                vector.reshape(
                    1,
                    -1,
                )
            )[0]
        )


        return {
            "status":
                "FORECAST_AVAILABLE",

            "future_risk":
                future_risk,

            "horizon_hours":
                float(
                    self.horizon_hours
                ),

            "naive_future_risk":
                current_risk,

            "uncertainty": {
                "type":
                    "TRAINING_RESIDUAL_STD_NOT_CALIBRATED",

                "value":
                    float(
                        self.training_residual_std
                    ),

                "validated_predictive_interval":
                    False,
            },

            "model_version":
                self.model_version,

            "model_schema_version":
                self.model_schema_version,

            "feature_count":
                len(
                    self.feature_names
                ),

            "scientific_guardrails": {
                "real_forecast_accuracy_validated":
                    False,

                "uncertainty_is_calibrated":
                    False,

                "naive_baseline_comparison_required":
                    True,

                "full_physical_digital_twin":
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

            "model_version":
                self.model_version,

            "model_type":
                "RIDGE_LINEAR_REGRESSION",

            "horizon_hours":
                float(
                    self.horizon_hours
                ),

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
                "coefficients":
                    list(
                        self.coefficients
                    ),

                "intercept":
                    float(
                        self.intercept
                    ),

                "l2_strength":
                    float(
                        self.l2_strength
                    ),
            },

            "uncertainty": {
                "method":
                    "TRAINING_RESIDUAL_STD",

                "value":
                    float(
                        self.training_residual_std
                    ),

                "calibrated":
                    False,
            },

            "scientific_guardrails": {
                "full_physical_digital_twin":
                    False,

                "real_forecast_accuracy_validated":
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
    ) -> "PredictiveRiskModel":

        if (
            payload.get(
                "model_schema_version"
            )
            != MODEL_SCHEMA_VERSION
        ):

            raise ValueError(
                "Unsupported forecast model schema."
            )

        feature_names = list(
            payload.get(
                "feature_names"
            )
        )

        if feature_names != MODEL_FEATURE_NAMES:

            raise ValueError(
                "Forecast feature schema mismatch."
            )

        scaler = payload.get(
            "scaler"
        )

        parameters = payload.get(
            "parameters"
        )

        uncertainty = payload.get(
            "uncertainty"
        )

        if not all(
            isinstance(
                item,
                Mapping,
            )
            for item in (
                scaler,
                parameters,
                uncertainty,
            )
        ):

            raise ValueError(
                "Forecast model artifact incomplete."
            )

        return cls(
            model_version=
                str(
                    payload.get(
                        "model_version"
                    )
                ),

            horizon_hours=
                _validate_horizon(
                    payload.get(
                        "horizon_hours"
                    )
                ),

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

            coefficients=[
                _finite_float(
                    value,
                    "coefficient",
                )
                for value in parameters[
                    "coefficients"
                ]
            ],

            intercept=
                _finite_float(
                    parameters[
                        "intercept"
                    ],
                    "intercept",
                ),

            l2_strength=
                _finite_float(
                    parameters[
                        "l2_strength"
                    ],
                    "l2_strength",
                ),

            training_residual_std=
                _finite_float(
                    uncertainty[
                        "value"
                    ],
                    "training_residual_std",
                ),
        )


def train_predictive_risk_model(
    training_records: Sequence[
        Mapping[str, Any]
    ],
    *,
    model_version: str,
    horizon_hours: float,
    l2_strength: float = 0.01,
) -> PredictiveRiskModel:

    if (
        not isinstance(
            model_version,
            str,
        )
        or not model_version.strip()
    ):

        raise ValueError(
            "model_version is required."
        )

    horizon = _validate_horizon(
        horizon_hours
    )

    l2 = _finite_float(
        l2_strength,
        "l2_strength",
    )

    if l2 <= 0.0:

        raise ValueError(
            "l2_strength must be > 0."
        )


    X, y = prepare_training_dataset(
        training_records,
        horizon_hours=
            horizon,
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


    design = np.column_stack(
        [
            np.ones(
                X_scaled.shape[0],
                dtype=np.float64,
            ),
            X_scaled,
        ]
    )


    penalty = np.eye(
        design.shape[1],
        dtype=np.float64,
    )


    penalty[
        0,
        0,
    ] = 0.0


    lhs = (
        design.T
        @ design
        + l2
        * penalty
    )


    rhs = (
        design.T
        @ y
    )


    parameters = np.linalg.solve(
        lhs,
        rhs,
    )


    intercept = float(
        parameters[0]
    )


    coefficients = (
        parameters[1:]
    )


    raw_training_predictions = (
        X_scaled
        @ coefficients
        + intercept
    )


    residuals = (
        y
        - raw_training_predictions
    )


    residual_std = math.sqrt(
        math.fsum(
            float(
                value
                * value
            )
            for value in residuals
        )
        / len(
            residuals
        )
    )


    return PredictiveRiskModel(
        model_version=
            model_version,

        horizon_hours=
            horizon,

        feature_names=
            list(
                MODEL_FEATURE_NAMES
            ),

        scaler_mean=[
            float(value)
            for value in mean
        ],

        scaler_scale=[
            float(value)
            for value in scale
        ],

        coefficients=[
            float(value)
            for value in coefficients
        ],

        intercept=
            intercept,

        l2_strength=
            l2,

        training_residual_std=
            float(
                residual_std
            ),
    )


def evaluate_predictive_risk_model(
    model: PredictiveRiskModel,
    evaluation_records: Sequence[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    if len(
        evaluation_records
    ) < 1:

        raise ValueError(
            "At least one evaluation record is required."
        )


    X = []

    y = []

    naive = []


    for record in evaluation_records:

        record_horizon = _validate_horizon(
            record.get(
                "horizon_hours"
            )
        )


        if not math.isclose(
            record_horizon,
            model.horizon_hours,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):

            raise ValueError(
                "Evaluation horizon does not match model horizon."
            )


        current = _risk_score(
            record.get(
                "current_risk_score"
            ),
            "current_risk_score",
        )


        X.append(
            extract_forecast_features(
                current_risk_score=
                    current,

                temporal_features=
                    record.get(
                        "temporal_features"
                    ),

                plant_delta=
                    record.get(
                        "plant_delta"
                    ),
            )
        )


        y.append(
            _risk_score(
                record.get(
                    "future_risk_score"
                ),
                "future_risk_score",
            )
        )


        naive.append(
            current
        )


    X = np.vstack(
        X
    ).astype(
        np.float64
    )


    y = np.asarray(
        y,
        dtype=np.float64,
    )


    naive = np.asarray(
        naive,
        dtype=np.float64,
    )


    predicted = model.predict_matrix(
        X
    )


    model_errors = (
        predicted
        - y
    )


    naive_errors = (
        naive
        - y
    )


    model_mae = math.fsum(
        abs(
            float(value)
        )
        for value in model_errors
    ) / len(y)


    naive_mae = math.fsum(
        abs(
            float(value)
        )
        for value in naive_errors
    ) / len(y)


    model_rmse = math.sqrt(
        math.fsum(
            float(
                value
                * value
            )
            for value in model_errors
        )
        / len(y)
    )


    naive_rmse = math.sqrt(
        math.fsum(
            float(
                value
                * value
            )
            for value in naive_errors
        )
        / len(y)
    )


    return {
        "model_schema_version":
            model.model_schema_version,

        "model_version":
            model.model_version,

        "horizon_hours":
            float(
                model.horizon_hours
            ),

        "sample_count":
            int(
                len(y)
            ),

        "model_metrics": {
            "mae":
                float(
                    model_mae
                ),

            "rmse":
                float(
                    model_rmse
                ),
        },

        "naive_baseline": {
            "method":
                "CURRENT_RISK_REMAINS_UNCHANGED",

            "mae":
                float(
                    naive_mae
                ),

            "rmse":
                float(
                    naive_rmse
                ),
        },

        "comparison": {
            "mae_improvement_vs_naive":
                float(
                    naive_mae
                    - model_mae
                ),

            "rmse_improvement_vs_naive":
                float(
                    naive_rmse
                    - model_rmse
                ),

            "model_beats_naive_on_supplied_dataset":
                bool(
                    (
                        model_mae
                        < naive_mae
                    )
                    and (
                        model_rmse
                        < naive_rmse
                    )
                ),

            "real_world_superiority_claimed":
                False,
        },

        "scientific_guardrails": {
            "metrics_only_describe_supplied_dataset":
                True,

            "real_forecast_accuracy_validated":
                False,

            "full_physical_digital_twin":
                False,

            "physical_action_authorized":
                False,
        },
    }
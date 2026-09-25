import unittest

import numpy as np

from src.predictive_risk import (
    MODEL_FEATURE_NAMES,
    PredictiveRiskModel,
    evaluate_predictive_risk_model,
    extract_forecast_features,
    train_predictive_risk_model,
)


def temporal(
    current,
    velocity,
    acceleration,
    *,
    soil_velocity=-1.0,
    temperature_velocity=0.5,
    humidity_velocity=-0.5,
):

    trend_code = (
        1.0
        if velocity > 0.1
        else (
            -1.0
            if velocity < -0.1
            else 0.0
        )
    )

    return {
        "schema_version":
            "greenpulse.temporal_intelligence.v1",

        "feature_vector_version":
            "temporal_feature_vector_v1",

        "status":
            "TEMPORAL_FEATURES_AVAILABLE",

        "feature_vector": {
            "names": [
                "risk_trend_code",
                "risk_velocity",
                "risk_acceleration",
                "temporal_consistency_code",
            ],

            "values": [
                trend_code,
                float(
                    velocity
                ),
                float(
                    acceleration
                ),
                0.0,
            ],
        },

        "sensor_trends": {
            "soil_moisture_pct": {
                "available":
                    True,

                "velocity":
                    float(
                        soil_velocity
                    ),
            },

            "temperature_c": {
                "available":
                    True,

                "velocity":
                    float(
                        temperature_velocity
                    ),
            },

            "humidity_pct": {
                "available":
                    True,

                "velocity":
                    float(
                        humidity_velocity
                    ),
            },
        },
    }


def record(
    current,
    velocity,
    acceleration,
    future,
    *,
    horizon=1.0,
):

    return {
        "current_risk_score":
            float(
                current
            ),

        "temporal_features":
            temporal(
                current,
                velocity,
                acceleration,
            ),

        "plant_delta":
            None,

        "future_risk_score":
            float(
                future
            ),

        "horizon_hours":
            float(
                horizon
            ),
    }


class TestPredictiveRisk(
    unittest.TestCase
):

    def setUp(self):

        self.training = [
            record(
                20,
                3,
                0.2,
                24,
            ),
            record(
                25,
                4,
                0.3,
                30,
            ),
            record(
                30,
                5,
                0.4,
                36,
            ),
            record(
                40,
                -2,
                -0.2,
                37,
            ),
            record(
                50,
                -3,
                -0.3,
                46,
            ),
            record(
                60,
                2,
                0.1,
                63,
            ),
            record(
                70,
                4,
                0.2,
                75,
            ),
            record(
                80,
                -4,
                -0.4,
                75,
            ),
        ]


    def test_feature_schema(self):

        vector = extract_forecast_features(
            current_risk_score=30,
            temporal_features=
                temporal(
                    30,
                    5,
                    0.4,
                ),
            plant_delta=None,
        )

        self.assertEqual(
            vector.shape,
            (
                len(
                    MODEL_FEATURE_NAMES
                ),
            ),
        )

        self.assertTrue(
            np.all(
                np.isfinite(
                    vector
                )
            )
        )


    def test_training_is_deterministic(self):

        first = train_predictive_risk_model(
            self.training,
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        second = train_predictive_risk_model(
            list(
                reversed(
                    self.training
                )
            ),
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        self.assertEqual(
            first.to_dict(),
            second.to_dict(),
        )


    def test_scaler_is_train_only(self):

        model = train_predictive_risk_model(
            self.training,
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        self.assertEqual(
            model.to_dict()[
                "scaler"
            ][
                "fit_scope"
            ],
            "TRAIN_ONLY",
        )


    def test_horizon_mixing_blocked(self):

        mixed = list(
            self.training
        )

        mixed[-1] = {
            **mixed[-1],
            "horizon_hours":
                3.0,
        }

        with self.assertRaises(
            ValueError
        ):

            train_predictive_risk_model(
                mixed,
                model_version=
                    "synthetic-v1",
                horizon_hours=1.0,
            )


    def test_forecast_output_contract(self):

        model = train_predictive_risk_model(
            self.training,
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        result = model.predict_record(
            current_risk_score=45,
            temporal_features=
                temporal(
                    45,
                    3,
                    0.2,
                ),
            plant_delta=None,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "FORECAST_AVAILABLE",
        )

        self.assertIn(
            "future_risk",
            result,
        )

        self.assertIn(
            "horizon_hours",
            result,
        )

        self.assertIn(
            "uncertainty",
            result,
        )

        self.assertEqual(
            result[
                "model_version"
            ],
            "synthetic-v1",
        )


    def test_forecast_is_bounded(self):

        model = train_predictive_risk_model(
            self.training,
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        result = model.predict_record(
            current_risk_score=99,
            temporal_features=
                temporal(
                    99,
                    50,
                    10,
                ),
            plant_delta=None,
        )

        self.assertGreaterEqual(
            result[
                "future_risk"
            ],
            0.0,
        )

        self.assertLessEqual(
            result[
                "future_risk"
            ],
            100.0,
        )


    def test_naive_baseline_is_reported(self):

        model = train_predictive_risk_model(
            self.training,
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        evaluation = [
            record(
                35,
                4,
                0.3,
                40,
            ),
            record(
                55,
                -2,
                -0.2,
                52,
            ),
        ]

        result = evaluate_predictive_risk_model(
            model,
            evaluation,
        )

        self.assertEqual(
            result[
                "naive_baseline"
            ][
                "method"
            ],
            "CURRENT_RISK_REMAINS_UNCHANGED",
        )

        self.assertIn(
            "mae",
            result[
                "naive_baseline"
            ],
        )

        self.assertIn(
            "rmse",
            result[
                "naive_baseline"
            ],
        )


    def test_serialization_round_trip(self):

        model = train_predictive_risk_model(
            self.training,
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        restored = (
            PredictiveRiskModel.from_dict(
                model.to_dict()
            )
        )

        self.assertEqual(
            model.to_dict(),
            restored.to_dict(),
        )


    def test_insufficient_temporal_history_blocks_prediction(self):

        model = train_predictive_risk_model(
            self.training,
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        bad_temporal = temporal(
            40,
            2,
            0.1,
        )

        bad_temporal[
            "status"
        ] = "INSUFFICIENT_HISTORY"

        bad_temporal[
            "feature_vector"
        ] = None

        result = model.predict_record(
            current_risk_score=40,
            temporal_features=
                bad_temporal,
            plant_delta=None,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED_INSUFFICIENT_TEMPORAL_HISTORY",
        )

        self.assertIsNone(
            result[
                "future_risk"
            ]
        )


    def test_no_digital_twin_or_physical_action_claim(self):

        model = train_predictive_risk_model(
            self.training,
            model_version=
                "synthetic-v1",
            horizon_hours=1.0,
        )

        result = model.predict_record(
            current_risk_score=45,
            temporal_features=
                temporal(
                    45,
                    2,
                    0.1,
                ),
            plant_delta=None,
        )

        guardrails = result[
            "scientific_guardrails"
        ]

        self.assertFalse(
            guardrails[
                "full_physical_digital_twin"
            ]
        )

        self.assertFalse(
            guardrails[
                "real_forecast_accuracy_validated"
            ]
        )

        self.assertFalse(
            guardrails[
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
import unittest
from datetime import datetime, timedelta, timezone

from src.sensor_feature_engineering import (
    build_sensor_feature_vector,
)

from src.sensor_only_baseline import (
    MODEL_FEATURE_NAMES,
    SensorOnlyBaselineModel,
    evaluate_sensor_only_baseline,
    train_sensor_only_baseline,
)


def packet(
    timestamp,
    soil,
    temperature,
    humidity,
):

    return {
        "plant_id":
            "P01",

        "timestamp":
            timestamp.isoformat(),

        "soil_moisture_pct":
            float(
                soil
            ),

        "temperature_c":
            float(
                temperature
            ),

        "humidity_pct":
            float(
                humidity
            ),

        "soil_calibrated":
            True,

        "source":
            "SIMULATED",
    }


def feature_record(
    timestamp,
    soil,
    temperature,
    humidity,
):

    current = packet(
        timestamp,
        soil,
        temperature,
        humidity,
    )

    return build_sensor_feature_vector(
        current,
        [],
    )


def labeled(
    timestamp,
    soil,
    temperature,
    humidity,
    label,
):

    return {
        "sensor_features":
            feature_record(
                timestamp,
                soil,
                temperature,
                humidity,
            ),

        "stress_label":
            label,
    }


class TestSensorOnlyBaseline(
    unittest.TestCase
):

    def setUp(self):

        self.now = datetime.now(
            timezone.utc
        ).replace(
            microsecond=0
        )

        self.training = [
            labeled(
                self.now
                - timedelta(seconds=i),
                80 - i,
                20 + 0.1 * i,
                60,
                0,
            )
            for i in range(6)
        ] + [
            labeled(
                self.now
                - timedelta(seconds=20 + i),
                20 + i,
                35 + 0.1 * i,
                35,
                1,
            )
            for i in range(6)
        ]


    def test_simulation_source_feature_is_excluded(self):

        self.assertNotIn(
            "source_is_simulated",
            MODEL_FEATURE_NAMES,
        )


    def test_model_uses_train_only_scaler(self):

        model = train_sensor_only_baseline(
            self.training,
            iterations=200,
        )

        self.assertEqual(
            model.to_dict()[
                "scaler"
            ][
                "fit_scope"
            ],
            "TRAIN_ONLY",
        )


    def test_training_is_deterministic_across_input_order(self):

        a = train_sensor_only_baseline(
            self.training,
            iterations=400,
        )

        b = train_sensor_only_baseline(
            list(
                reversed(
                    self.training
                )
            ),
            iterations=400,
        )

        self.assertEqual(
            a.to_dict(),
            b.to_dict(),
        )


    def test_model_separates_simple_synthetic_fixture(self):

        model = train_sensor_only_baseline(
            self.training,
            iterations=1500,
        )

        low_risk = feature_record(
            self.now,
            78,
            21,
            60,
        )

        high_risk = feature_record(
            self.now,
            22,
            36,
            35,
        )

        low = model.predict_feature_record(
            low_risk
        )

        high = model.predict_feature_record(
            high_risk
        )

        self.assertLess(
            low[
                "stress_probability"
            ],
            high[
                "stress_probability"
            ],
        )

        self.assertEqual(
            low[
                "predicted_label"
            ],
            0,
        )

        self.assertEqual(
            high[
                "predicted_label"
            ],
            1,
        )


    def test_serialization_round_trip(self):

        model = train_sensor_only_baseline(
            self.training,
            iterations=300,
        )

        payload = model.to_dict()

        restored = (
            SensorOnlyBaselineModel.from_dict(
                payload
            )
        )

        self.assertEqual(
            model.to_dict(),
            restored.to_dict(),
        )


    def test_evaluation_metrics(self):

        model = train_sensor_only_baseline(
            self.training,
            iterations=1500,
        )

        evaluation = [
            labeled(
                self.now,
                75,
                21,
                60,
                0,
            ),
            labeled(
                self.now
                - timedelta(seconds=1),
                25,
                36,
                35,
                1,
            ),
            labeled(
                self.now
                - timedelta(seconds=2),
                73,
                22,
                60,
                0,
            ),
            labeled(
                self.now
                - timedelta(seconds=3),
                23,
                35,
                35,
                1,
            ),
        ]

        result = evaluate_sensor_only_baseline(
            model,
            evaluation,
        )

        self.assertEqual(
            result[
                "sample_count"
            ],
            4,
        )

        self.assertEqual(
            sum(
                result[
                    "confusion"
                ].values()
            ),
            4,
        )

        for key in [
            "accuracy",
            "precision",
            "recall",
            "f1",
            "false_positive_rate",
            "false_negative_rate",
        ]:

            self.assertGreaterEqual(
                result[
                    "metrics"
                ][
                    key
                ],
                0.0,
            )

            self.assertLessEqual(
                result[
                    "metrics"
                ][
                    key
                ],
                1.0,
            )


    def test_invalid_nonbinary_label_blocked(self):

        bad = list(
            self.training
        )

        bad[0] = {
            **bad[0],
            "stress_label":
                2,
        }

        with self.assertRaises(
            ValueError
        ):

            train_sensor_only_baseline(
                bad
            )


    def test_single_class_training_blocked(self):

        one_class = [
            {
                **item,
                "stress_label":
                    0,
            }
            for item in self.training
        ]

        with self.assertRaises(
            ValueError
        ):

            train_sensor_only_baseline(
                one_class
            )


    def test_prediction_does_not_authorize_action(self):

        model = train_sensor_only_baseline(
            self.training,
            iterations=300,
        )

        result = model.predict_feature_record(
            feature_record(
                self.now,
                20,
                37,
                30,
            )
        )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "physical_action_authorized"
            ]
        )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "probability_is_real_world_calibrated"
            ]
        )


    def test_constant_features_do_not_break_scaling(self):

        model = train_sensor_only_baseline(
            self.training,
            iterations=50,
        )

        self.assertTrue(
            all(
                value > 0
                for value in model.scaler_scale
            )
        )


if __name__ == "__main__":
    unittest.main()
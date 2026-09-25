import unittest
from datetime import datetime, timezone

import numpy as np

from src.visual_features import (
    extract_visual_features,
)

from src.sensor_feature_engineering import (
    build_sensor_feature_vector,
)

from src.feature_fusion import (
    FUSION_FEATURE_NAMES,
    build_multimodal_feature_vector,
)

from src.multimodal_fusion_model import (
    MultimodalFusionModel,
    evaluate_multimodal_fusion_model,
    extract_fusion_vector,
    train_multimodal_fusion_model,
)


def visual(
    value,
    confidence,
):

    image = np.full(
        (16, 16, 3),
        value,
        dtype=np.uint8,
    )

    return extract_visual_features(
        image,
        visual_confidence=confidence,
        confidence_source="classification",
    )


def sensor(
    soil,
    temperature,
    humidity,
):

    now = datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    )

    packet = {
        "plant_id":
            "P01",

        "timestamp":
            now.isoformat(),

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

    return build_sensor_feature_vector(
        packet,
        [],
    )


def fused(
    image_value,
    confidence,
    soil,
    temperature,
    humidity,
):

    return build_multimodal_feature_vector(
        visual_features=visual(
            image_value,
            confidence,
        ),

        sensor_features=sensor(
            soil,
            temperature,
            humidity,
        ),

        plant_delta=None,

        temporal_features=None,

        time_sync_status="SYNCED",
    )


def labeled(
    image_value,
    confidence,
    soil,
    temperature,
    humidity,
    label,
):

    return {
        "fused_features":
            fused(
                image_value,
                confidence,
                soil,
                temperature,
                humidity,
            ),

        "stress_label":
            label,
    }


class TestMultimodalFusionModel(
    unittest.TestCase
):

    def setUp(self):

        self.training = [
            labeled(
                60 + i,
                0.95 - i * 0.01,
                75 - i,
                22 + i * 0.1,
                65,
                0,
            )
            for i in range(6)
        ] + [
            labeled(
                190 + i * 5,
                0.60 - i * 0.01,
                25 + i,
                35 + i * 0.1,
                35,
                1,
            )
            for i in range(6)
        ]


    def test_fusion_vector_schema(self):

        vector = extract_fusion_vector(
            self.training[0][
                "fused_features"
            ]
        )

        self.assertEqual(
            vector.shape,
            (
                len(
                    FUSION_FEATURE_NAMES
                ),
            ),
        )

        self.assertTrue(
            np.all(
                np.isfinite(vector)
            )
        )


    def test_train_only_scaler(self):

        model = train_multimodal_fusion_model(
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


    def test_training_deterministic_across_input_order(self):

        first = train_multimodal_fusion_model(
            self.training,
            iterations=400,
        )

        second = train_multimodal_fusion_model(
            list(
                reversed(
                    self.training
                )
            ),
            iterations=400,
        )

        self.assertEqual(
            first.to_dict(),
            second.to_dict(),
        )


    def test_simple_synthetic_fixture_separable(self):

        model = train_multimodal_fusion_model(
            self.training,
            iterations=1500,
        )

        low = fused(
            62,
            0.94,
            78,
            22,
            65,
        )

        high = fused(
            225,
            0.50,
            20,
            37,
            30,
        )

        low_result = model.predict_record(
            low
        )

        high_result = model.predict_record(
            high
        )

        self.assertLess(
            low_result[
                "positive_class_probability"
            ],
            high_result[
                "positive_class_probability"
            ],
        )

        self.assertEqual(
            low_result[
                "predicted_label"
            ],
            0,
        )

        self.assertEqual(
            high_result[
                "predicted_label"
            ],
            1,
        )


    def test_serialization_round_trip(self):

        model = train_multimodal_fusion_model(
            self.training,
            iterations=300,
        )

        restored = (
            MultimodalFusionModel.from_dict(
                model.to_dict()
            )
        )

        self.assertEqual(
            model.to_dict(),
            restored.to_dict(),
        )


    def test_evaluation_metrics(self):

        model = train_multimodal_fusion_model(
            self.training,
            iterations=1200,
        )

        evaluation = [
            labeled(
                61,
                0.94,
                76,
                22,
                65,
                0,
            ),
            labeled(
                65,
                0.92,
                72,
                23,
                65,
                0,
            ),
            labeled(
                210,
                0.55,
                22,
                36,
                32,
                1,
            ),
            labeled(
                225,
                0.48,
                18,
                38,
                30,
                1,
            ),
        ]

        result = (
            evaluate_multimodal_fusion_model(
                model,
                evaluation,
            )
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

        for name in (
            "accuracy",
            "precision",
            "recall",
            "f1",
            "false_positive_rate",
            "false_negative_rate",
        ):

            self.assertGreaterEqual(
                result[
                    "metrics"
                ][name],
                0.0,
            )

            self.assertLessEqual(
                result[
                    "metrics"
                ][name],
                1.0,
            )


    def test_single_class_training_blocked(self):

        one_class = [
            {
                **record,
                "stress_label":
                    0,
            }
            for record in self.training
        ]

        with self.assertRaises(
            ValueError
        ):

            train_multimodal_fusion_model(
                one_class
            )


    def test_invalid_label_blocked(self):

        bad = list(
            self.training
        )

        bad[0] = {
            **bad[0],
            "stress_label":
                3,
        }

        with self.assertRaises(
            ValueError
        ):

            train_multimodal_fusion_model(
                bad
            )


    def test_wrong_vector_version_blocked(self):

        bad = {
            **self.training[0][
                "fused_features"
            ]
        }

        bad[
            "feature_vector_version"
        ] = "wrong"

        with self.assertRaises(
            ValueError
        ):

            extract_fusion_vector(
                bad
            )


    def test_no_operational_probability_or_action(self):

        model = train_multimodal_fusion_model(
            self.training,
            iterations=300,
        )

        result = model.predict_record(
            self.training[-1][
                "fused_features"
            ]
        )

        self.assertIsNone(
            result[
                "operational_water_stress_probability"
            ]
        )

        guardrails = result[
            "scientific_guardrails"
        ]

        self.assertFalse(
            guardrails[
                "probability_is_real_world_calibrated"
            ]
        )

        self.assertFalse(
            guardrails[
                "multimodal_superiority_established"
            ]
        )

        self.assertFalse(
            guardrails[
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
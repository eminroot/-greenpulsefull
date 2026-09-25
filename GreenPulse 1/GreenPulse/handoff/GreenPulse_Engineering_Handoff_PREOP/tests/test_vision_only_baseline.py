import unittest

import numpy as np

from src.visual_features import (
    extract_visual_features,
)

from src.plant_baseline import (
    build_plant_baseline,
    compute_plant_delta,
)

from src.vision_only_baseline import (
    MODEL_FEATURE_NAMES,
    VisionOnlyBaselineModel,
    evaluate_vision_only_baseline,
    extract_model_vector,
    train_vision_only_baseline,
)


def make_visual(
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


def build_fixture():

    baseline_visual = make_visual(
        60,
        0.95,
    )

    observations = [
        {
            "observation_id":
                f"B{i}",

            "plant_id":
                "P01",

            "is_healthy":
                True,

            "visual_features":
                baseline_visual,
        }
        for i in range(3)
    ]

    baseline = build_plant_baseline(
        observations,
        plant_id="P01",
    )

    return baseline


def labeled_record(
    value,
    confidence,
    label,
    baseline,
):

    visual = make_visual(
        value,
        confidence,
    )

    delta = compute_plant_delta(
        visual,
        baseline,
    )

    return {
        "visual_features":
            visual,

        "plant_delta":
            delta,

        "stress_label":
            label,
    }


class TestVisionOnlyBaseline(
    unittest.TestCase
):

    def setUp(self):

        self.baseline = build_fixture()

        self.training = [
            labeled_record(
                55 + i,
                0.95 - 0.01 * i,
                0,
                self.baseline,
            )
            for i in range(6)
        ] + [
            labeled_record(
                190 + i * 5,
                0.65 - 0.01 * i,
                1,
                self.baseline,
            )
            for i in range(6)
        ]


    def test_feature_schema_is_numeric_and_stable(self):

        vector = extract_model_vector(
            self.training[0][
                "visual_features"
            ],
            self.training[0][
                "plant_delta"
            ],
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


    def test_disease_class_name_is_not_model_feature(self):

        joined = " ".join(
            MODEL_FEATURE_NAMES
        ).lower()

        self.assertNotIn(
            "disease_class",
            joined,
        )

        self.assertNotIn(
            "predicted_class",
            joined,
        )


    def test_gradcam_is_not_model_feature(self):

        joined = " ".join(
            MODEL_FEATURE_NAMES
        ).lower()

        self.assertNotIn(
            "gradcam",
            joined,
        )

        self.assertNotIn(
            "heatmap",
            joined,
        )


    def test_scaler_fit_scope_is_train_only(self):

        model = train_vision_only_baseline(
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

        first = train_vision_only_baseline(
            self.training,
            iterations=400,
        )

        second = train_vision_only_baseline(
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


    def test_simple_synthetic_fixture_is_separable(self):

        model = train_vision_only_baseline(
            self.training,
            iterations=1500,
        )

        low = labeled_record(
            62,
            0.93,
            0,
            self.baseline,
        )

        high = labeled_record(
            220,
            0.55,
            1,
            self.baseline,
        )

        low_result = model.predict_record(
            low[
                "visual_features"
            ],
            low[
                "plant_delta"
            ],
        )

        high_result = model.predict_record(
            high[
                "visual_features"
            ],
            high[
                "plant_delta"
            ],
        )

        self.assertLess(
            low_result[
                "stress_probability"
            ],
            high_result[
                "stress_probability"
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

        model = train_vision_only_baseline(
            self.training,
            iterations=300,
        )

        restored = (
            VisionOnlyBaselineModel.from_dict(
                model.to_dict()
            )
        )

        self.assertEqual(
            model.to_dict(),
            restored.to_dict(),
        )


    def test_evaluation_metrics(self):

        model = train_vision_only_baseline(
            self.training,
            iterations=1500,
        )

        evaluation = [
            labeled_record(
                58,
                0.94,
                0,
                self.baseline,
            ),
            labeled_record(
                64,
                0.92,
                0,
                self.baseline,
            ),
            labeled_record(
                205,
                0.60,
                1,
                self.baseline,
            ),
            labeled_record(
                230,
                0.50,
                1,
                self.baseline,
            ),
        ]

        result = evaluate_vision_only_baseline(
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

        for key in (
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


    def test_missing_plant_delta_is_explicitly_supported(self):

        visual = make_visual(
            100,
            0.8,
        )

        vector = extract_model_vector(
            visual,
            None,
        )

        self.assertEqual(
            vector[-1],
            0.0,
        )


    def test_single_class_training_is_blocked(self):

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

            train_vision_only_baseline(
                one_class
            )


    def test_prediction_does_not_authorize_physical_action(self):

        model = train_vision_only_baseline(
            self.training,
            iterations=300,
        )

        record = self.training[-1]

        result = model.predict_record(
            record[
                "visual_features"
            ],
            record[
                "plant_delta"
            ],
        )

        guardrails = result[
            "scientific_guardrails"
        ]

        self.assertFalse(
            guardrails[
                "probability_is_water_stress_probability"
            ]
        )

        self.assertFalse(
            guardrails[
                "probability_is_real_world_calibrated"
            ]
        )

        self.assertFalse(
            guardrails[
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
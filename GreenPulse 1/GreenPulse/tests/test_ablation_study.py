import unittest

from src.ablation_study import (
    REAL_SCOPE,
    SCHEMA_VERSION,
    SYNTHETIC_SCOPE,
    binary_classification_metrics,
    evaluate_three_way_ablation,
)


class TestAblationStudy(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.ablation_study.v1",
        )


    def test_perfect_metrics(self):

        result = binary_classification_metrics(
            [0, 0, 1, 1],
            [0, 0, 1, 1],
        )

        self.assertEqual(
            result["precision"],
            1.0,
        )

        self.assertEqual(
            result["recall"],
            1.0,
        )

        self.assertEqual(
            result["f1"],
            1.0,
        )

        self.assertEqual(
            result["false_positive_rate"],
            0.0,
        )

        self.assertEqual(
            result["false_negative_rate"],
            0.0,
        )


    def test_confusion_counts(self):

        result = binary_classification_metrics(
            [0, 0, 1, 1],
            [0, 1, 0, 1],
        )

        self.assertEqual(
            (
                result["tp"],
                result["tn"],
                result["fp"],
                result["fn"],
            ),
            (1, 1, 1, 1),
        )


    def test_empty_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            binary_classification_metrics(
                [],
                [],
            )


    def test_length_mismatch_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            binary_classification_metrics(
                [0, 1],
                [0],
            )


    def test_non_binary_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            binary_classification_metrics(
                [0, 2],
                [0, 1],
            )


    def test_three_way_metrics_present(self):

        result = evaluate_three_way_ablation(
            y_true=[0, 0, 1, 1],
            sensor_only=[0, 1, 1, 0],
            vision_only=[0, 0, 1, 0],
            fusion=[0, 0, 1, 1],
            evidence_scope=SYNTHETIC_SCOPE,
        )

        self.assertEqual(
            set(result["metrics"]),
            {
                "sensor_only",
                "vision_only",
                "vision_sensor_fusion",
            },
        )


    def test_synthetic_fusion_improvement_not_claimable(self):

        result = evaluate_three_way_ablation(
            y_true=[0, 0, 1, 1],
            sensor_only=[0, 1, 1, 0],
            vision_only=[0, 0, 1, 0],
            fusion=[0, 0, 1, 1],
            evidence_scope=SYNTHETIC_SCOPE,
        )

        self.assertTrue(
            result[
                "comparisons"
            ][
                "fusion_f1_above_both"
            ]
        )

        self.assertFalse(
            result[
                "claim_boundary"
            ][
                "multimodal_benefit_claim_permitted"
            ]
        )


    def test_real_scope_can_permit_measured_f1_claim(self):

        result = evaluate_three_way_ablation(
            y_true=[0, 0, 1, 1],
            sensor_only=[0, 1, 1, 0],
            vision_only=[0, 0, 1, 0],
            fusion=[0, 0, 1, 1],
            evidence_scope=REAL_SCOPE,
        )

        self.assertTrue(
            result[
                "claim_boundary"
            ][
                "multimodal_benefit_claim_permitted"
            ]
        )


    def test_real_scope_without_improvement_blocks_claim(self):

        result = evaluate_three_way_ablation(
            y_true=[0, 0, 1, 1],
            sensor_only=[0, 0, 1, 1],
            vision_only=[0, 0, 1, 1],
            fusion=[0, 1, 1, 0],
            evidence_scope=REAL_SCOPE,
        )

        self.assertFalse(
            result[
                "claim_boundary"
            ][
                "multimodal_benefit_claim_permitted"
            ]
        )


    def test_three_way_length_mismatch_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            evaluate_three_way_ablation(
                y_true=[0, 1],
                sensor_only=[0, 1],
                vision_only=[0],
                fusion=[0, 1],
                evidence_scope=SYNTHETIC_SCOPE,
            )


    def test_unknown_scope_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            evaluate_three_way_ablation(
                y_true=[0, 1],
                sensor_only=[0, 1],
                vision_only=[0, 1],
                fusion=[0, 1],
                evidence_scope="UNKNOWN",
            )


if __name__ == "__main__":
    unittest.main()
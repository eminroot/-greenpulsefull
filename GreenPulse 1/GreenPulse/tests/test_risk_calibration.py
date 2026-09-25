import unittest

import numpy as np

from src.risk_calibration import (
    CANDIDATE_STATUS,
    PlattCalibrator,
    build_candidate_calibration_artifact,
    calibration_metrics,
    compare_calibration,
    fit_platt_calibrator,
    optimize_band_thresholds,
    optimize_threshold,
)

from src.stress_risk_score import (
    ALLOWED_PROBABILITY_SOURCE,
    build_stress_risk_score,
)


PROBABILITIES = [
    0.08,
    0.18,
    0.31,
    0.42,
    0.47,
    0.56,
    0.61,
    0.73,
    0.82,
    0.91,
]

LABELS = [
    0,
    0,
    1,
    0,
    1,
    0,
    1,
    1,
    0,
    1,
]


POLICIES = {
    "MONITOR": {
        "false_negative_cost":
            8.0,

        "false_positive_cost":
            1.0,
    },

    "WARNING": {
        "false_negative_cost":
            3.0,

        "false_positive_cost":
            2.0,
    },

    "ACTION": {
        "false_negative_cost":
            1.0,

        "false_positive_cost":
            8.0,
    },
}


class TestRiskCalibration(
    unittest.TestCase
):

    def test_calibration_metrics_are_finite(self):

        result = calibration_metrics(
            PROBABILITIES,
            LABELS,
            bins=5,
        )

        for name in (
            "brier_score",
            "log_loss",
            "expected_calibration_error",
        ):

            self.assertTrue(
                np.isfinite(
                    result[name]
                )
            )

        self.assertGreaterEqual(
            result[
                "expected_calibration_error"
            ],
            0.0,
        )

        self.assertLessEqual(
            result[
                "expected_calibration_error"
            ],
            1.0,
        )


    def test_platt_training_is_deterministic(self):

        first = fit_platt_calibrator(
            PROBABILITIES,
            LABELS,
            iterations=500,
        )

        second = fit_platt_calibrator(
            list(
                reversed(
                    PROBABILITIES
                )
            ),
            list(
                reversed(
                    LABELS
                )
            ),
            iterations=500,
        )

        self.assertEqual(
            first.to_dict(),
            second.to_dict(),
        )


    def test_single_class_calibration_is_blocked(self):

        with self.assertRaises(
            ValueError
        ):

            fit_platt_calibrator(
                PROBABILITIES,
                [0] * len(
                    PROBABILITIES
                ),
            )


    def test_calibrated_probabilities_remain_bounded(self):

        calibrator = fit_platt_calibrator(
            PROBABILITIES,
            LABELS,
            iterations=500,
        )

        calibrated = calibrator.predict(
            PROBABILITIES
        )

        self.assertTrue(
            np.all(
                calibrated >= 0.0
            )
        )

        self.assertTrue(
            np.all(
                calibrated <= 1.0
            )
        )


    def test_calibrator_serialization_round_trip(self):

        calibrator = fit_platt_calibrator(
            PROBABILITIES,
            LABELS,
            iterations=300,
        )

        restored = PlattCalibrator.from_dict(
            calibrator.to_dict()
        )

        self.assertEqual(
            calibrator.to_dict(),
            restored.to_dict(),
        )


    def test_threshold_requires_explicit_costs(self):

        with self.assertRaises(
            ValueError
        ):

            optimize_threshold(
                PROBABILITIES,
                LABELS,
                false_negative_cost=0.0,
                false_positive_cost=1.0,
            )


    def test_threshold_tradeoff_is_documented(self):

        result = optimize_threshold(
            PROBABILITIES,
            LABELS,
            false_negative_cost=5.0,
            false_positive_cost=2.0,
        )

        self.assertIn(
            "false_negative",
            result,
        )

        self.assertIn(
            "false_positive",
            result,
        )

        self.assertIn(
            "weighted_error_cost",
            result,
        )

        self.assertFalse(
            result[
                "operationally_approved"
            ]
        )


    def test_band_thresholds_never_auto_approve(self):

        result = optimize_band_thresholds(
            PROBABILITIES,
            LABELS,
            policies=POLICIES,
        )

        self.assertIn(
            result[
                "status"
            ],
            {
                "CANDIDATE_THRESHOLDS_ONLY",
                "REVIEW_REQUIRED_NON_MONOTONIC_THRESHOLDS",
            },
        )

        self.assertFalse(
            result[
                "operationally_approved"
            ]
        )

        self.assertTrue(
            result[
                "tradeoff_documented"
            ]
        )


    def test_candidate_artifact_is_not_validated(self):

        calibrator = fit_platt_calibrator(
            PROBABILITIES,
            LABELS,
            iterations=300,
        )

        comparison = compare_calibration(
            calibrator,
            PROBABILITIES,
            LABELS,
            bins=5,
        )

        thresholds = optimize_band_thresholds(
            calibrator.predict(
                PROBABILITIES
            ).tolist(),
            LABELS,
            policies=POLICIES,
        )

        artifact = (
            build_candidate_calibration_artifact(
                candidate_version=
                    "synthetic-test-v1",

                model_version=
                    "fusion-test-v1",

                feature_vector_version=
                    "multimodal_feature_vector_v1",

                calibrator=
                    calibrator,

                calibration_comparison=
                    comparison,

                threshold_candidates=
                    thresholds,

                calibration_dataset_id=
                    "SYNTHETIC_CALIBRATION_UNIT_TEST",

                threshold_dataset_id=
                    "SYNTHETIC_THRESHOLD_UNIT_TEST",
            )
        )

        self.assertEqual(
            artifact[
                "status"
            ],
            CANDIDATE_STATUS,
        )

        self.assertFalse(
            artifact[
                "scientific_guardrails"
            ][
                "validated"
            ]
        )


    def test_layer26_rejects_candidate_artifact(self):

        calibrator = fit_platt_calibrator(
            PROBABILITIES,
            LABELS,
            iterations=200,
        )

        comparison = compare_calibration(
            calibrator,
            PROBABILITIES,
            LABELS,
            bins=5,
        )

        thresholds = optimize_band_thresholds(
            calibrator.predict(
                PROBABILITIES
            ).tolist(),
            LABELS,
            policies=POLICIES,
        )

        artifact = (
            build_candidate_calibration_artifact(
                candidate_version=
                    "synthetic-test-v1",

                model_version=
                    "fusion-test-v1",

                feature_vector_version=
                    "multimodal_feature_vector_v1",

                calibrator=
                    calibrator,

                calibration_comparison=
                    comparison,

                threshold_candidates=
                    thresholds,

                calibration_dataset_id=
                    "SYNTHETIC_A",

                threshold_dataset_id=
                    "SYNTHETIC_B",
            )
        )

        with self.assertRaises(
            ValueError
        ):

            build_stress_risk_score(
                calibrated_probability=0.7,
                probability_source=
                    ALLOWED_PROBABILITY_SOURCE,
                calibration_artifact=
                    artifact,
                model_version=
                    "fusion-test-v1",
                feature_vector_version=
                    "multimodal_feature_vector_v1",
                timestamp=
                    "2026-09-24T12:00:00+00:00",
            )


if __name__ == "__main__":
    unittest.main()
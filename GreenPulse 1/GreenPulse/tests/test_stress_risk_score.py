import unittest
from datetime import datetime, timezone

from src.stress_risk_score import (
    ALLOWED_PROBABILITY_SOURCE,
    build_stress_risk_score,
)


MODEL_VERSION = "fusion-model-test-v1"

FEATURE_VERSION = (
    "multimodal_feature_vector_v1"
)


def timestamp():

    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


def calibration():

    return {
        "schema_version":
            "greenpulse.risk_calibration.v1",

        "status":
            "VALIDATED",

        "version":
            "synthetic-calibration-test-v1",

        "model_version":
            MODEL_VERSION,

        "feature_vector_version":
            FEATURE_VERSION,
    }


class TestStressRiskScore(
    unittest.TestCase
):

    def test_missing_calibration_blocks_score(self):

        result = build_stress_risk_score(
            calibrated_probability=0.7,
            probability_source=
                ALLOWED_PROBABILITY_SOURCE,
            calibration_artifact=None,
            model_version=
                MODEL_VERSION,
            feature_vector_version=
                FEATURE_VERSION,
            timestamp=
                timestamp(),
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED",
        )

        self.assertIsNone(
            result[
                "stress_risk_score"
            ]
        )


    def test_zero_probability_maps_to_zero(self):

        result = build_stress_risk_score(
            calibrated_probability=0.0,
            probability_source=
                ALLOWED_PROBABILITY_SOURCE,
            calibration_artifact=
                calibration(),
            model_version=
                MODEL_VERSION,
            feature_vector_version=
                FEATURE_VERSION,
            timestamp=
                timestamp(),
        )

        self.assertEqual(
            result[
                "stress_risk_score"
            ],
            0.0,
        )


    def test_one_probability_maps_to_100(self):

        result = build_stress_risk_score(
            calibrated_probability=1.0,
            probability_source=
                ALLOWED_PROBABILITY_SOURCE,
            calibration_artifact=
                calibration(),
            model_version=
                MODEL_VERSION,
            feature_vector_version=
                FEATURE_VERSION,
            timestamp=
                timestamp(),
        )

        self.assertEqual(
            result[
                "stress_risk_score"
            ],
            100.0,
        )


    def test_probability_maps_linearly(self):

        result = build_stress_risk_score(
            calibrated_probability=0.375,
            probability_source=
                ALLOWED_PROBABILITY_SOURCE,
            calibration_artifact=
                calibration(),
            model_version=
                MODEL_VERSION,
            feature_vector_version=
                FEATURE_VERSION,
            timestamp=
                timestamp(),
        )

        self.assertEqual(
            result[
                "stress_risk_score"
            ],
            37.5,
        )


    def test_invalid_probability_blocked(self):

        with self.assertRaises(
            ValueError
        ):

            build_stress_risk_score(
                calibrated_probability=1.2,
                probability_source=
                    ALLOWED_PROBABILITY_SOURCE,
                calibration_artifact=
                    calibration(),
                model_version=
                    MODEL_VERSION,
                feature_vector_version=
                    FEATURE_VERSION,
                timestamp=
                    timestamp(),
            )


    def test_raw_disease_confidence_source_blocked(self):

        with self.assertRaises(
            ValueError
        ):

            build_stress_risk_score(
                calibrated_probability=0.9,
                probability_source=
                    "DISEASE_CLASSIFICATION_CONFIDENCE",
                calibration_artifact=
                    calibration(),
                model_version=
                    MODEL_VERSION,
                feature_vector_version=
                    FEATURE_VERSION,
                timestamp=
                    timestamp(),
            )


    def test_model_version_mismatch_blocked(self):

        artifact = calibration()

        artifact[
            "model_version"
        ] = "wrong-model"

        with self.assertRaisesRegex(
            ValueError,
            "CALIBRATION_MODEL_VERSION_MISMATCH",
        ):

            build_stress_risk_score(
                calibrated_probability=0.5,
                probability_source=
                    ALLOWED_PROBABILITY_SOURCE,
                calibration_artifact=
                    artifact,
                model_version=
                    MODEL_VERSION,
                feature_vector_version=
                    FEATURE_VERSION,
                timestamp=
                    timestamp(),
            )


    def test_feature_version_mismatch_blocked(self):

        artifact = calibration()

        artifact[
            "feature_vector_version"
        ] = "wrong-vector"

        with self.assertRaisesRegex(
            ValueError,
            "CALIBRATION_FEATURE_VERSION_MISMATCH",
        ):

            build_stress_risk_score(
                calibrated_probability=0.5,
                probability_source=
                    ALLOWED_PROBABILITY_SOURCE,
                calibration_artifact=
                    artifact,
                model_version=
                    MODEL_VERSION,
                feature_vector_version=
                    FEATURE_VERSION,
                timestamp=
                    timestamp(),
            )


    def test_timezone_is_required(self):

        with self.assertRaises(
            ValueError
        ):

            build_stress_risk_score(
                calibrated_probability=0.5,
                probability_source=
                    ALLOWED_PROBABILITY_SOURCE,
                calibration_artifact=
                    calibration(),
                model_version=
                    MODEL_VERSION,
                feature_vector_version=
                    FEATURE_VERSION,
                timestamp=
                    "2026-09-24T12:00:00",
            )


    def test_thresholds_and_actuation_not_assigned(self):

        result = build_stress_risk_score(
            calibrated_probability=0.8,
            probability_source=
                ALLOWED_PROBABILITY_SOURCE,
            calibration_artifact=
                calibration(),
            model_version=
                MODEL_VERSION,
            feature_vector_version=
                FEATURE_VERSION,
            timestamp=
                timestamp(),
        )

        self.assertIsNone(
            result[
                "risk_band"
            ]
        )

        guards = result[
            "scientific_guardrails"
        ]

        self.assertTrue(
            guards[
                "thresholds_owned_by_layer_27"
            ]
        )

        self.assertFalse(
            guards[
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
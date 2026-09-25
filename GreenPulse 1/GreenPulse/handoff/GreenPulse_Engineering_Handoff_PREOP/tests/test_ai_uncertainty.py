import unittest

from src.ai_uncertainty import (
    evaluate_uncertainty,
)


def good_image():

    return {
        "status":
            "IMAGE_OK",

        "reason":
            None,

        "eligible_for_inference":
            True,

        "blur_score":
            12.0,

        "blur_threshold_validated":
            False,
    }


def evaluate_clean(
    **overrides,
):

    args = {
        "model_confidence":
            0.90,

        "model_confidence_source":
            "SYNTHETIC_UNIT_TEST_MODEL",

        "low_confidence_threshold":
            0.60,

        "confidence_threshold_validated":
            True,

        "image_quality":
            good_image(),

        "sensor_validation":
            (
                "VALID",
                "all_checks_passed",
            ),

        "inference_error":
            False,

        "ood_suspected":
            False,

        "unusual_feature_combination":
            False,
    }

    args.update(
        overrides
    )

    return evaluate_uncertainty(
        **args
    )


class TestAIUncertainty(
    unittest.TestCase
):

    def test_clean_signals_can_reach_confident(self):

        result = evaluate_clean()

        self.assertEqual(
            result[
                "state"
            ],
            "CONFIDENT",
        )

        self.assertEqual(
            result[
                "uncertainty_action"
            ],
            "PASS_TO_SAFETY_POLICY",
        )


    def test_low_confidence_is_uncertain(self):

        result = evaluate_clean(
            model_confidence=0.40,
        )

        self.assertEqual(
            result[
                "state"
            ],
            "UNCERTAIN",
        )

        self.assertIn(
            "LOW_CONFIDENCE",
            result[
                "reason_codes"
            ],
        )


    def test_unvalidated_confidence_threshold_is_uncertain(self):

        result = evaluate_clean(
            confidence_threshold_validated=False,
        )

        self.assertEqual(
            result[
                "state"
            ],
            "UNCERTAIN",
        )

        self.assertIn(
            "CONFIDENCE_THRESHOLD_NOT_VALIDATED",
            result[
                "reason_codes"
            ],
        )


    def test_image_quality_failure_requires_recheck(self):

        bad_image = good_image()

        bad_image[
            "status"
        ] = "IMAGE_TOO_DARK"

        bad_image[
            "eligible_for_inference"
        ] = False

        result = evaluate_clean(
            image_quality=
                bad_image
        )

        self.assertEqual(
            result[
                "state"
            ],
            "RECHECK_REQUIRED",
        )

        self.assertIn(
            "IMAGE_QUALITY_FAILURE",
            result[
                "reason_codes"
            ],
        )


    def test_nonoperational_sensor_states_require_recheck(self):

        cases = [
            (
                "MISSING",
                "field",
            ),
            (
                "INVALID",
                "field",
            ),
            (
                "STALE",
                "timestamp",
            ),
            (
                "VALID_SIMULATED",
                "simulation_only",
            ),
        ]

        for sensor_result in cases:

            with self.subTest(
                sensor_result=
                    sensor_result
            ):

                result = evaluate_clean(
                    sensor_validation=
                        sensor_result
                )

                self.assertEqual(
                    result[
                        "state"
                    ],
                    "RECHECK_REQUIRED",
                )


    def test_ood_requires_recheck(self):

        result = evaluate_clean(
            ood_suspected=True,
        )

        self.assertEqual(
            result[
                "state"
            ],
            "RECHECK_REQUIRED",
        )

        self.assertIn(
            "OOD_SUSPECTED",
            result[
                "reason_codes"
            ],
        )


    def test_unusual_feature_combination_requires_recheck(self):

        result = evaluate_clean(
            unusual_feature_combination=True,
        )

        self.assertEqual(
            result[
                "state"
            ],
            "RECHECK_REQUIRED",
        )

        self.assertIn(
            "UNUSUAL_FEATURE_COMBINATION",
            result[
                "reason_codes"
            ],
        )


    def test_model_failure_requires_recheck(self):

        result = evaluate_clean(
            inference_error=True,
        )

        self.assertEqual(
            result[
                "state"
            ],
            "RECHECK_REQUIRED",
        )

        self.assertIn(
            "MODEL_FAILURE",
            result[
                "reason_codes"
            ],
        )


    def test_missing_confidence_requires_recheck(self):

        result = evaluate_clean(
            model_confidence=None,
            model_confidence_source=None,
        )

        self.assertEqual(
            result[
                "state"
            ],
            "RECHECK_REQUIRED",
        )

        self.assertIn(
            "MODEL_CONFIDENCE_MISSING",
            result[
                "reason_codes"
            ],
        )


    def test_unvalidated_blur_is_not_hard_gate(self):

        result = evaluate_clean()

        self.assertEqual(
            result[
                "state"
            ],
            "CONFIDENT",
        )

        self.assertFalse(
            result[
                "image_quality"
            ][
                "blur_used_as_hard_gate"
            ]
        )


    def test_invalid_confidence_is_blocked(self):

        with self.assertRaises(
            ValueError
        ):

            evaluate_clean(
                model_confidence=1.5,
            )


    def test_layer_never_authorizes_physical_action(self):

        result = evaluate_clean()

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "physical_action_authorized"
            ]
        )

        uncertain = evaluate_clean(
            model_confidence=0.2,
        )

        self.assertFalse(
            uncertain[
                "scientific_guardrails"
            ][
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
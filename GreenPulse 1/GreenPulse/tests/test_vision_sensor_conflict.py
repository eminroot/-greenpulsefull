import unittest

from src.vision_sensor_conflict import (
    evaluate_vision_sensor_conflict,
)


def evaluate(
    **overrides,
):

    args = {
        "vision_state":
            "NORMAL",

        "sensor_state":
            "NORMAL",

        "vision_source":
            "SYNTHETIC_UNIT_TEST_VISION",

        "sensor_source":
            "SYNTHETIC_UNIT_TEST_SENSOR",

        "vision_signal_validated":
            True,

        "sensor_signal_validated":
            True,
    }

    args.update(
        overrides
    )

    return evaluate_vision_sensor_conflict(
        **args
    )


class TestVisionSensorConflict(
    unittest.TestCase
):

    def test_normal_normal_no_conflict(self):

        result = evaluate()

        self.assertEqual(
            result[
                "status"
            ],
            "NO_CONFLICT",
        )

        self.assertFalse(
            result[
                "vision_sensor_conflict"
            ]
        )

        self.assertEqual(
            result[
                "routing"
            ],
            "MONITOR",
        )


    def test_high_high_no_conflict(self):

        result = evaluate(
            vision_state=
                "HIGH_STRESS",

            sensor_state=
                "HIGH_STRESS",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "NO_CONFLICT",
        )

        self.assertFalse(
            result[
                "vision_sensor_conflict"
            ]
        )


    def test_vision_high_sensor_normal_conflict(self):

        result = evaluate(
            vision_state=
                "HIGH_STRESS",

            sensor_state=
                "NORMAL",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "VISION_SENSOR_CONFLICT",
        )

        self.assertTrue(
            result[
                "vision_sensor_conflict"
            ]
        )

        self.assertEqual(
            result[
                "routing"
            ],
            "RECHECK",
        )


    def test_vision_normal_sensor_high_conflict(self):

        result = evaluate(
            vision_state=
                "NORMAL",

            sensor_state=
                "HIGH_STRESS",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "VISION_SENSOR_CONFLICT",
        )

        self.assertTrue(
            result[
                "vision_sensor_conflict"
            ]
        )


    def test_unknown_vision_requires_recheck(self):

        result = evaluate(
            vision_state=
                "UNKNOWN",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "CONFLICT_NOT_EVALUABLE",
        )

        self.assertEqual(
            result[
                "routing"
            ],
            "RECHECK",
        )


    def test_unknown_sensor_requires_recheck(self):

        result = evaluate(
            sensor_state=
                "UNKNOWN",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "CONFLICT_NOT_EVALUABLE",
        )


    def test_unvalidated_vision_requires_recheck(self):

        result = evaluate(
            vision_signal_validated=
                False,
        )

        self.assertFalse(
            result[
                "conflict_evaluable"
            ]
        )

        self.assertEqual(
            result[
                "routing"
            ],
            "RECHECK",
        )


    def test_unvalidated_sensor_requires_recheck(self):

        result = evaluate(
            sensor_signal_validated=
                False,
        )

        self.assertFalse(
            result[
                "conflict_evaluable"
            ]
        )


    def test_invalid_state_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            evaluate(
                vision_state=
                    "MEDIUM_STRESS",
            )


    def test_sources_required(self):

        with self.assertRaises(
            ValueError
        ):

            evaluate(
                vision_source=
                    "",
            )


    def test_no_numeric_threshold_inference(self):

        result = evaluate()

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "numeric_thresholds_inferred_here"
            ]
        )


    def test_never_authorizes_physical_action(self):

        result = evaluate(
            vision_state=
                "HIGH_STRESS",

            sensor_state=
                "NORMAL",
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
                "conflict_authorizes_forced_actuation"
            ]
        )


if __name__ == "__main__":
    unittest.main()
import unittest

from src.decision_safety import (
    evaluate_decision_safety,
    load_safety_policy,
)


def request_decision():

    return {
        "decision":
            "IRRIGATION_REQUEST"
    }


def context(
    **overrides,
):

    result = {
        "model_confidence":
            0.90,

        "stress_risk_score":
            85.0,

        "confirmation_count":
            3,

        "seconds_since_last_request":
            900.0,

        "requested_action_duration_seconds":
            10.0,

        "camera_valid":
            True,

        "sensor_valid":
            True,

        "manual_override":
            "NONE",
    }

    result.update(
        overrides
    )

    return result


def synthetic_policy():

    return {
        "schema_version":
            "greenpulse.safety_policy.v1",

        "policy_version":
            "synthetic-unit-test-v1",

        "policy_status":
            "SYNTHETIC_TEST_ONLY",

        "autonomous_request_enabled":
            False,

        "minimum_confidence":
            0.80,

        "minimum_risk_score":
            70.0,

        "confirmation_count":
            2,

        "cooldown_seconds":
            600.0,

        "maximum_requested_action_duration_seconds":
            15.0,

        "require_camera_valid":
            True,

        "require_sensor_valid":
            True,

        "manual_override": {
            "enabled":
                True,

            "allowed_modes": [
                "NONE",
                "FORCE_BLOCK",
                "MANUAL_REVIEW",
            ],

            "physical_safety_bypass_allowed":
                False,
        },
    }


class TestDecisionSafety(
    unittest.TestCase
):

    def test_real_config_loads_as_unvalidated(self):

        policy = load_safety_policy()

        self.assertEqual(
            policy[
                "policy_status"
            ],
            "DEVELOPMENT_ONLY_UNVALIDATED",
        )

        self.assertFalse(
            policy[
                "autonomous_request_enabled"
            ]
        )


    def test_real_config_blocks_irrigation_request(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(),
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED_POLICY_NOT_OPERATIONALLY_VALIDATED",
        )

        self.assertFalse(
            result[
                "request_allowed_by_safety_policy"
            ]
        )


    def test_synthetic_policy_can_test_logic_only(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "SYNTHETIC_POLICY_LOGIC_PASS",
        )

        self.assertFalse(
            result[
                "request_allowed_by_safety_policy"
            ]
        )


    def test_low_confidence_blocks(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    model_confidence=0.50
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED_SAFETY_CONSTRAINT",
        )

        self.assertIn(
            "MINIMUM_CONFIDENCE_NOT_MET",
            result[
                "reason_codes"
            ],
        )


    def test_low_risk_blocks(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    stress_risk_score=50.0
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertIn(
            "MINIMUM_RISK_NOT_MET",
            result[
                "reason_codes"
            ],
        )


    def test_confirmation_count_blocks(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    confirmation_count=1
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertIn(
            "CONFIRMATION_COUNT_NOT_MET",
            result[
                "reason_codes"
            ],
        )


    def test_cooldown_blocks(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    seconds_since_last_request=100.0
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertIn(
            "COOLDOWN_ACTIVE",
            result[
                "reason_codes"
            ],
        )


    def test_maximum_duration_blocks(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    requested_action_duration_seconds=30.0
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertIn(
            "REQUESTED_ACTION_DURATION_EXCEEDS_LIMIT",
            result[
                "reason_codes"
            ],
        )


    def test_camera_invalid_blocks(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    camera_valid=False
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertIn(
            "CAMERA_INVALID",
            result[
                "reason_codes"
            ],
        )


    def test_sensor_invalid_blocks(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    sensor_valid=False
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertIn(
            "SENSOR_INVALID",
            result[
                "reason_codes"
            ],
        )


    def test_force_block_manual_override(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    manual_override=
                        "FORCE_BLOCK"
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED_MANUAL_OVERRIDE",
        )


    def test_manual_review_override(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(
                    manual_override=
                        "MANUAL_REVIEW"
                ),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "routing"
            ],
            "MANUAL_REVIEW",
        )


    def test_non_irrigation_decision_is_not_promoted(self):

        result = evaluate_decision_safety(
            decision_result={
                "decision":
                    "MONITOR"
            },

            safety_context=
                context(),
        )

        self.assertEqual(
            result[
                "status"
            ],
            "NO_IRRIGATION_REQUEST_TO_EVALUATE",
        )

        self.assertFalse(
            result[
                "request_allowed_by_safety_policy"
            ]
        )


    def test_synthetic_policy_requires_test_mode(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(),

            policy=
                synthetic_policy(),

            test_only=
                False,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED_SYNTHETIC_POLICY_OUTSIDE_TEST_MODE",
        )


    def test_layer_never_dispatches_hardware(self):

        result = evaluate_decision_safety(
            decision_result=
                request_decision(),

            safety_context=
                context(),

            policy=
                synthetic_policy(),

            test_only=
                True,
        )

        self.assertFalse(
            result[
                "hardware_dispatch_permitted"
            ]
        )

        self.assertFalse(
            result[
                "physical_actuation_authorized"
            ]
        )

        self.assertIsNone(
            result[
                "actuator_command"
            ]
        )


if __name__ == "__main__":
    unittest.main()
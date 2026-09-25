import unittest

from src.failure_safe_state import (
    POLICY_SCHEMA_VERSION,
    REQUIRED_FAILURES,
    RESULT_SCHEMA_VERSION,
    evaluate_failure_safe_state,
    load_failure_policy,
    validate_failure_policy,
)


class TestFailureSafeState(
    unittest.TestCase
):

    def test_schema_versions(self):

        self.assertEqual(
            POLICY_SCHEMA_VERSION,
            "greenpulse.failure_safe_state_policy.v1",
        )

        self.assertEqual(
            RESULT_SCHEMA_VERSION,
            "greenpulse.failure_safe_state_result.v1",
        )


    def test_default_policy_valid(self):

        policy = load_failure_policy()

        self.assertEqual(
            policy[
                "policy_status"
            ],
            "DEVELOPMENT_ONLY_UNVALIDATED",
        )


    def test_all_required_failures_are_mapped(self):

        policy = load_failure_policy()

        self.assertEqual(
            set(
                policy[
                    "failure_mapping"
                ]
            ),
            set(
                REQUIRED_FAILURES
            ),
        )


    def test_camera_missing_goes_safe_mode(self):

        result = evaluate_failure_safe_state(
            [
                "CAMERA_MISSING"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "SAFE_MODE",
        )


    def test_camera_timeout_goes_safe_mode(self):

        result = evaluate_failure_safe_state(
            [
                "CAMERA_TIMEOUT"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "SAFE_MODE",
        )


    def test_blurred_image_goes_manual_review(self):

        result = evaluate_failure_safe_state(
            [
                "BLURRED_IMAGE"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "MANUAL_REVIEW",
        )


    def test_sensor_missing_goes_manual_review(self):

        result = evaluate_failure_safe_state(
            [
                "SENSOR_MISSING"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "MANUAL_REVIEW",
        )


    def test_sensor_invalid_goes_manual_review(self):

        result = evaluate_failure_safe_state(
            [
                "SENSOR_INVALID"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "MANUAL_REVIEW",
        )


    def test_sensor_stale_goes_monitor(self):

        result = evaluate_failure_safe_state(
            [
                "SENSOR_STALE"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "MONITOR",
        )


    def test_wifi_failure_goes_safe_mode(self):

        result = evaluate_failure_safe_state(
            [
                "WIFI_FAILURE"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "SAFE_MODE",
        )


    def test_low_confidence_goes_manual_review(self):

        result = evaluate_failure_safe_state(
            [
                "LOW_CONFIDENCE"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "MANUAL_REVIEW",
        )


    def test_conflict_goes_manual_review(self):

        result = evaluate_failure_safe_state(
            [
                "VISION_SENSOR_CONFLICT"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "MANUAL_REVIEW",
        )


    def test_db_failure_goes_safe_mode(self):

        result = evaluate_failure_safe_state(
            [
                "DB_FAILURE"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "SAFE_MODE",
        )


    def test_hardware_timeout_goes_safe_mode(self):

        result = evaluate_failure_safe_state(
            [
                "HARDWARE_TIMEOUT"
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "SAFE_MODE",
        )


    def test_most_conservative_state_wins(self):

        result = evaluate_failure_safe_state(
            [
                "SENSOR_STALE",
                "LOW_CONFIDENCE",
                "HARDWARE_TIMEOUT",
            ]
        )

        self.assertEqual(
            result[
                "selected_safe_state"
            ],
            "SAFE_MODE",
        )


    def test_duplicate_failure_is_deduplicated(self):

        result = evaluate_failure_safe_state(
            [
                "sensor stale",
                "SENSOR_STALE",
            ]
        )

        self.assertEqual(
            result[
                "failure_codes"
            ],
            [
                "SENSOR_STALE"
            ],
        )


    def test_unknown_failure_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            evaluate_failure_safe_state(
                [
                    "UNKNOWN_FAILURE"
                ]
            )


    def test_empty_failure_list_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            evaluate_failure_safe_state(
                []
            )


    def test_blind_actuation_is_blocked(self):

        result = evaluate_failure_safe_state(
            [
                "LOW_CONFIDENCE"
            ]
        )

        guard = result[
            "actuation_guard"
        ]

        self.assertFalse(
            guard[
                "hardware_dispatch_permitted"
            ]
        )

        self.assertFalse(
            guard[
                "physical_actuation_authorized"
            ]
        )

        self.assertFalse(
            guard[
                "blind_actuation_permitted"
            ]
        )


    def test_engine_never_requests_crash(self):

        result = evaluate_failure_safe_state(
            [
                "DB_FAILURE"
            ]
        )

        self.assertFalse(
            result[
                "system_behavior"
            ][
                "crash_requested"
            ]
        )


    def test_normal_actuation_is_blocked_on_failure(self):

        result = evaluate_failure_safe_state(
            [
                "SENSOR_STALE"
            ]
        )

        self.assertFalse(
            result[
                "system_behavior"
            ][
                "continue_normal_actuation"
            ]
        )


    def test_policy_cannot_enable_blind_actuation(self):

        policy = load_failure_policy()

        policy[
            "actuation_policy"
        ][
            "blind_actuation_permitted"
        ] = True


        with self.assertRaises(
            ValueError
        ):

            validate_failure_policy(
                policy
            )


if __name__ == "__main__":
    unittest.main()
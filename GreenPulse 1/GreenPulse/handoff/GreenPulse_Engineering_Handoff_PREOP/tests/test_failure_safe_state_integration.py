import copy
import unittest

from src.failure_safe_state_integration import (
    SCHEMA_VERSION,
    apply_failure_safe_state,
)


def source_output():

    return {
        "schema_version":
            "greenpulse.master_observation_output.v1",

        "observation_id":
            "OBS-001",

        "plant_id":
            "P01",

        "decision": {
            "action":
                "IRRIGATION_REQUEST",

            "reason_codes": [
                "SYNTHETIC_TEST_DECISION"
            ],
        },
    }


class TestFailureSafeStateIntegration(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.failure_safe_state_integration.v1",
        )


    def test_camera_missing_suppresses_normal_decision(self):

        result = apply_failure_safe_state(
            source_output(),
            [
                "CAMERA_MISSING"
            ],
        )

        self.assertEqual(
            result[
                "effective_system_state"
            ],
            "SAFE_MODE",
        )

        self.assertTrue(
            result[
                "normal_decision_suppressed"
            ]
        )


    def test_sensor_stale_degrades_to_monitor(self):

        result = apply_failure_safe_state(
            source_output(),
            [
                "SENSOR_STALE"
            ],
        )

        self.assertEqual(
            result[
                "effective_system_state"
            ],
            "MONITOR",
        )


    def test_low_confidence_degrades_to_manual_review(self):

        result = apply_failure_safe_state(
            source_output(),
            [
                "LOW_CONFIDENCE"
            ],
        )

        self.assertEqual(
            result[
                "effective_system_state"
            ],
            "MANUAL_REVIEW",
        )


    def test_original_decision_preserved_for_audit(self):

        source = source_output()

        result = apply_failure_safe_state(
            source,
            [
                "DB_FAILURE"
            ],
        )

        self.assertEqual(
            result[
                "original_decision"
            ],
            source[
                "decision"
            ],
        )


    def test_source_output_not_mutated(self):

        source = source_output()

        before = copy.deepcopy(
            source
        )

        apply_failure_safe_state(
            source,
            [
                "HARDWARE_TIMEOUT"
            ],
        )

        self.assertEqual(
            source,
            before,
        )


    def test_hardware_dispatch_is_blocked(self):

        result = apply_failure_safe_state(
            source_output(),
            [
                "VISION_SENSOR_CONFLICT"
            ],
        )

        self.assertFalse(
            result[
                "actuation_guard"
            ][
                "hardware_dispatch_permitted_by_ai"
            ]
        )


    def test_physical_actuation_is_blocked(self):

        result = apply_failure_safe_state(
            source_output(),
            [
                "CAMERA_TIMEOUT"
            ],
        )

        self.assertFalse(
            result[
                "actuation_guard"
            ][
                "physical_actuation_authorized_by_ai"
            ]
        )

        self.assertFalse(
            result[
                "execution"
            ][
                "physical_actuation"
            ]
        )


    def test_multiple_failures_choose_most_conservative_state(self):

        result = apply_failure_safe_state(
            source_output(),
            [
                "SENSOR_STALE",
                "LOW_CONFIDENCE",
                "WIFI_FAILURE",
            ],
        )

        self.assertEqual(
            result[
                "effective_system_state"
            ],
            "SAFE_MODE",
        )


    def test_source_identity_is_preserved(self):

        result = apply_failure_safe_state(
            source_output(),
            [
                "BLURRED_IMAGE"
            ],
        )

        self.assertEqual(
            result[
                "observation_id"
            ],
            "OBS-001",
        )

        self.assertEqual(
            result[
                "plant_id"
            ],
            "P01",
        )


    def test_non_mapping_source_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            apply_failure_safe_state(
                [],
                [
                    "DB_FAILURE"
                ],
            )


    def test_failure_policy_remains_unvalidated(self):

        result = apply_failure_safe_state(
            source_output(),
            [
                "SENSOR_INVALID"
            ],
        )

        self.assertEqual(
            result[
                "failure_policy_status"
            ],
            "DEVELOPMENT_ONLY_UNVALIDATED",
        )


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads(
        (ROOT / relative).read_text(
            encoding="utf-8"
        )
    )


class TestFinalReleaseHandoff(unittest.TestCase):

    def test_manifest_exists(self):
        self.assertTrue(
            (
                ROOT
                / "release"
                / "greenpulse_release_manifest_v1.json"
            ).is_file()
        )

    def test_manifest_does_not_claim_final_release(self):
        data = load(
            "release/greenpulse_release_manifest_v1.json"
        )

        self.assertFalse(
            data[
                "final_operational_release_complete"
            ]
        )

        self.assertFalse(
            data[
                "claim_boundary"
            ][
                "operational_release_complete"
            ]
        )

    def test_hailo_remains_blocked(self):
        data = load(
            "release/greenpulse_release_manifest_v1.json"
        )

        self.assertFalse(
            data[
                "blockers"
            ][
                "engineer1_hailo_approval"
            ]
        )

        self.assertFalse(
            data[
                "blockers"
            ][
                "hef_available"
            ]
        )

    def test_backend_handoff_fields(self):
        data = load(
            "release/backend_handoff_v1.json"
        )

        self.assertEqual(
            len(
                data[
                    "standard_output_fields"
                ]
            ),
            12,
        )

    def test_backend_failure_codes_present(self):
        data = load(
            "release/backend_handoff_v1.json"
        )

        self.assertIn(
            "HARDWARE_TIMEOUT",
            data[
                "failure_error_codes"
            ],
        )

    def test_frontend_dictionary_has_12_fields(self):
        data = load(
            "release/frontend_field_dictionary_v1.json"
        )

        self.assertEqual(
            len(
                data[
                    "fields"
                ]
            ),
            12,
        )

    def test_frontend_dictionary_required_metadata(self):
        data = load(
            "release/frontend_field_dictionary_v1.json"
        )

        for field in data["fields"]:
            for key in (
                "datatype",
                "unit",
                "range",
                "null_behavior",
                "update_frequency",
            ):
                self.assertIn(
                    key,
                    field,
                )

    def test_unknown_ranges_not_invented(self):
        data = load(
            "release/frontend_field_dictionary_v1.json"
        )

        self.assertFalse(
            data[
                "claim_boundary"
            ][
                "unknown_ranges_invented"
            ]
        )

    def test_hardware_schemas_exist(self):
        for relative in (
            "release/schemas/sensor_payload_schema_v1.json",
            "release/schemas/actuator_request_schema_v1.json",
            "release/schemas/ack_error_schema_v1.json",
        ):
            self.assertTrue(
                (
                    ROOT
                    / relative
                ).is_file()
            )

    def test_ack_contract(self):
        data = load(
            "release/schemas/ack_error_schema_v1.json"
        )

        values = (
            data[
                "properties"
            ][
                "status"
            ][
                "enum"
            ]
        )

        self.assertEqual(
            values,
            [
                "ACK",
                "FAIL",
                "TIMEOUT",
            ],
        )

    def test_hardware_safety_blocks_blind_actuation(self):
        data = load(
            "release/hardware_handoff_v1.json"
        )

        self.assertFalse(
            data[
                "safety_expectations"
            ][
                "blind_actuation_allowed"
            ]
        )

    def test_hardware_not_claimed_real(self):
        data = load(
            "release/hardware_handoff_v1.json"
        )

        self.assertFalse(
            data[
                "claim_boundary"
            ][
                "real_hardware_integration_complete"
            ]
        )

    def test_examples_are_explicitly_illustrative(self):
        request = load(
            "release/examples/example_request_v1.json"
        )

        response = load(
            "release/examples/example_response_v1.json"
        )

        self.assertTrue(
            request[
                "illustrative_only"
            ]
        )

        self.assertTrue(
            response[
                "illustrative_only"
            ]
        )

    def test_readme_and_scripts_exist(self):
        for relative in (
            "release/README.md",
            "release/install.ps1",
            "release/start.ps1",
        ):
            self.assertTrue(
                (
                    ROOT
                    / relative
                ).is_file()
            )


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)

from src.actuator_request_contract import (
    SCHEMA_VERSION,
    build_standard_actuator_request,
    prepare_actuator_handoff,
    validate_ack_linkage,
)


COMMAND_ID = (
    "123e4567-e89b-12d3-a456-426614174000"
)


def standard_output(
    *,
    decision="IRRIGATION_REQUEST",
    risk_score=82.0,
):

    return {
        "schema_version":
            "greenpulse.standard_ai_output.v1",

        "observation_id":
            "OBS-TEST-38",

        "plant_id":
            "P01",

        "decision":
            decision,

        "reason_codes": [
            "TEMPORAL_CONFIRMATION",
            "RISK_TREND_RISING",
        ],

        "risk":
            (
                {
                    "status":
                        "AVAILABLE",

                    "stress_risk_score":
                        risk_score,
                }
                if risk_score
                is not None
                else None
            ),

        "model_versions": {
            "decision":
                "greenpulse.decision_intelligence.v1",
        },
    }


def safety_result(
    *,
    allowed=True,
    policy_status="OPERATIONAL_VALIDATED",
):

    return {
        "policy_version":
            "safety-policy-test-v1",

        "policy_status":
            policy_status,

        "request_allowed_by_safety_policy":
            allowed,

        "hardware_dispatch_permitted":
            False,

        "physical_actuation_authorized":
            False,
    }


class TestActuatorRequestContract(
    unittest.TestCase
):

    def test_schema_version_constant(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.standard_actuator_request.v1",
        )


    def test_test_only_request_contains_required_fields(self):

        request = build_standard_actuator_request(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    policy_status=
                        "SYNTHETIC_TEST_ONLY",
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "SYNTHETIC_TEST_ONLY",

            command_id=
                COMMAND_ID,

            test_only=
                True,
        )

        required = {
            "command_id",
            "plant_id",
            "action",
            "risk_score",
            "confidence",
            "requested_duration_seconds",
            "reason_codes",
            "decision_version",
        }

        self.assertTrue(
            required.issubset(
                request
            )
        )


    def test_request_validates_against_schema(self):

        request = build_standard_actuator_request(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    policy_status=
                        "SYNTHETIC_TEST_ONLY",
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "SYNTHETIC_TEST_ONLY",

            command_id=
                COMMAND_ID,

            test_only=
                True,
        )

        schema = json.loads(
            Path(
                "configs/actuator_request_schema_v2.json"
            ).read_text(
                encoding="utf-8-sig"
            )
        )

        Draft202012Validator.check_schema(
            schema
        )

        validator = Draft202012Validator(
            schema,
            format_checker=
                FormatChecker(),
        )

        errors = list(
            validator.iter_errors(
                request
            )
        )

        self.assertEqual(
            errors,
            [],
        )


    def test_ai_never_controls_electrical_layer(self):

        request = build_standard_actuator_request(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    policy_status=
                        "SYNTHETIC_TEST_ONLY",
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "SYNTHETIC_TEST_ONLY",

            command_id=
                COMMAND_ID,

            test_only=
                True,
        )

        self.assertFalse(
            request[
                "direct_electrical_control"
            ]
        )

        self.assertFalse(
            request[
                "relay_or_mosfet_controlled_by_ai"
            ]
        )


    def test_request_does_not_permit_dispatch(self):

        request = build_standard_actuator_request(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    policy_status=
                        "SYNTHETIC_TEST_ONLY",
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "SYNTHETIC_TEST_ONLY",

            command_id=
                COMMAND_ID,

            test_only=
                True,
        )

        self.assertFalse(
            request[
                "hardware_dispatch_permitted_by_ai"
            ]
        )

        self.assertFalse(
            request[
                "physical_actuation_authorized_by_ai"
            ]
        )


    def test_missing_real_risk_blocks_handoff(self):

        result = prepare_actuator_handoff(
            standard_output=
                standard_output(
                    risk_score=None
                ),

            safety_result=
                safety_result(),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "CALIBRATED_MULTIMODAL_FUSION",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED",
        )

        self.assertIsNone(
            result[
                "actuator_request"
            ]
        )


    def test_non_irrigation_decision_blocks_handoff(self):

        result = prepare_actuator_handoff(
            standard_output=
                standard_output(
                    decision="MONITOR"
                ),

            safety_result=
                safety_result(),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "CALIBRATED_MULTIMODAL_FUSION",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED",
        )


    def test_safety_policy_must_allow_request(self):

        result = prepare_actuator_handoff(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    allowed=False
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "CALIBRATED_MULTIMODAL_FUSION",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED",
        )


    def test_operational_request_rejects_disease_confidence(self):

        result = prepare_actuator_handoff(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.99,

            confidence_source=
                "DISEASE_CLASSIFICATION",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "BLOCKED",
        )


    def test_test_only_fixture_can_create_request(self):

        result = prepare_actuator_handoff(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    policy_status=
                        "SYNTHETIC_TEST_ONLY",
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "SYNTHETIC_TEST_ONLY",

            command_id=
                COMMAND_ID,

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "TEST_REQUEST_CREATED",
        )

        self.assertIsNotNone(
            result[
                "actuator_request"
            ]
        )

        self.assertFalse(
            result[
                "hardware_dispatch_permitted"
            ]
        )


    def test_command_id_is_preserved(self):

        result = prepare_actuator_handoff(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    policy_status=
                        "SYNTHETIC_TEST_ONLY",
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "SYNTHETIC_TEST_ONLY",

            command_id=
                COMMAND_ID,

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "actuator_request"
            ][
                "command_id"
            ],
            COMMAND_ID,
        )


    def test_ack_linkage_matches_command_id(self):

        request = build_standard_actuator_request(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    policy_status=
                        "SYNTHETIC_TEST_ONLY",
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "SYNTHETIC_TEST_ONLY",

            command_id=
                COMMAND_ID,

            test_only=
                True,
        )

        linkage = validate_ack_linkage(
            actuator_request=
                request,

            hardware_ack={
                "command_id":
                    COMMAND_ID,

                "status":
                    "SIMULATED_EXECUTED",
            },
        )

        self.assertTrue(
            linkage[
                "linked"
            ]
        )

        self.assertFalse(
            linkage[
                "real_hardware_ack_validated"
            ]
        )


    def test_ack_linkage_rejects_mismatch(self):

        request = build_standard_actuator_request(
            standard_output=
                standard_output(),

            safety_result=
                safety_result(
                    policy_status=
                        "SYNTHETIC_TEST_ONLY",
                ),

            requested_duration_seconds=
                5,

            decision_confidence=
                0.88,

            confidence_source=
                "SYNTHETIC_TEST_ONLY",

            command_id=
                COMMAND_ID,

            test_only=
                True,
        )

        linkage = validate_ack_linkage(
            actuator_request=
                request,

            hardware_ack={
                "command_id":
                    (
                        "223e4567-e89b-12d3-a456-"
                        "426614174000"
                    )
            },
        )

        self.assertFalse(
            linkage[
                "linked"
            ]
        )

        self.assertEqual(
            linkage[
                "reason"
            ],
            "COMMAND_ID_MISMATCH",
        )


if __name__ == "__main__":
    unittest.main()
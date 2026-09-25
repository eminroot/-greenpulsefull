import json
import unittest
from pathlib import Path

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)

from src.hardware_ack_state import (
    SCHEMA_VERSION,
    normalize_real_ack_claim,
    normalize_simulated_ack,
    validate_request_ack_linkage,
)


COMMAND_ID = (
    "123e4567-e89b-12d3-a456-426614174000"
)

OBSERVATION_ID = (
    "223e4567-e89b-12d3-a456-426614174000"
)


def simulated_ack(
    status="SIMULATED_EXECUTED",
    error_code=None,
):

    return {
        "simulator_version":
            "0.2.0",

        "command_id":
            COMMAND_ID,

        "observation_id":
            OBSERVATION_ID,

        "plant_id":
            "TEST-P01",

        "target":
            "MAIN_IRRIGATION_PUMP",

        "status":
            status,

        "error_code":
            error_code,

        "timestamp":
            "2026-09-24T12:00:00+00:00",

        "simulated":
            True,

        "physical_actuation":
            False,

        "real_hardware_ack":
            None,
    }


class TestHardwareAckState(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.hardware_action_state.v1",
        )


    def test_simulated_executed_maps_to_executed(self):

        result = normalize_simulated_ack(
            simulated_ack()
        )

        self.assertEqual(
            result[
                "action_state"
            ],
            "EXECUTED",
        )

        self.assertTrue(
            result[
                "simulated"
            ]
        )

        self.assertFalse(
            result[
                "real_hardware_ack_validated"
            ]
        )


    def test_simulated_rejected_maps_to_rejected(self):

        result = normalize_simulated_ack(
            simulated_ack(
                status=
                    "SIMULATED_REJECTED",

                error_code=
                    "COMMAND_NOT_AUTHORIZED",
            )
        )

        self.assertEqual(
            result[
                "action_state"
            ],
            "REJECTED",
        )


    def test_simulated_failed_maps_to_failed(self):

        result = normalize_simulated_ack(
            simulated_ack(
                status=
                    "SIMULATED_FAILED",

                error_code=
                    "SIMULATED_PUMP_FAILURE",
            )
        )

        self.assertEqual(
            result[
                "action_state"
            ],
            "FAILED",
        )


    def test_simulated_timeout_maps_to_timeout(self):

        result = normalize_simulated_ack(
            simulated_ack(
                status=
                    "SIMULATED_TIMEOUT",

                error_code=
                    "SIMULATED_CONTROLLER_TIMEOUT",
            )
        )

        self.assertEqual(
            result[
                "action_state"
            ],
            "TIMEOUT",
        )


    def test_nonexecuted_state_requires_error_code(self):

        with self.assertRaises(
            ValueError
        ):

            normalize_simulated_ack(
                simulated_ack(
                    status=
                        "SIMULATED_FAILED",

                    error_code=
                        None,
                )
            )


    def test_simulated_ack_cannot_claim_physical_action(self):

        ack = simulated_ack()

        ack[
            "physical_actuation"
        ] = True

        with self.assertRaises(
            ValueError
        ):

            normalize_simulated_ack(
                ack
            )


    def test_simulated_ack_validates_against_schema(self):

        result = normalize_simulated_ack(
            simulated_ack()
        )

        schema = json.loads(
            Path(
                "configs/hardware_action_state_schema_v1.json"
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
                result
            )
        )

        self.assertEqual(
            errors,
            [],
        )


    def test_real_ack_claim_remains_unverified(self):

        result = normalize_real_ack_claim(
            {
                "command_id":
                    COMMAND_ID,

                "observation_id":
                    OBSERVATION_ID,

                "plant_id":
                    "P01",

                "target":
                    "MAIN_IRRIGATION_PUMP",

                "action_state":
                    "EXECUTED",

                "error_code":
                    None,

                "timestamp":
                    "2026-09-24T12:00:00+00:00",
            }
        )

        self.assertTrue(
            result[
                "real_hardware_ack"
            ]
        )

        self.assertFalse(
            result[
                "real_hardware_ack_validated"
            ]
        )

        self.assertIsNone(
            result[
                "physical_actuation"
            ]
        )


    def test_real_failed_claim_requires_error(self):

        with self.assertRaises(
            ValueError
        ):

            normalize_real_ack_claim(
                {
                    "command_id":
                        COMMAND_ID,

                    "observation_id":
                        OBSERVATION_ID,

                    "plant_id":
                        "P01",

                    "target":
                        "MAIN_IRRIGATION_PUMP",

                    "action_state":
                        "FAILED",

                    "error_code":
                        None,

                    "timestamp":
                        "2026-09-24T12:00:00+00:00",
                }
            )


    def test_request_ack_linkage(self):

        result = normalize_simulated_ack(
            simulated_ack()
        )

        linkage = validate_request_ack_linkage(
            actuator_request={
                "command_id":
                    COMMAND_ID,
            },

            action_state=
                result,
        )

        self.assertTrue(
            linkage[
                "linked"
            ]
        )


    def test_request_ack_linkage_mismatch(self):

        result = normalize_simulated_ack(
            simulated_ack()
        )

        linkage = validate_request_ack_linkage(
            actuator_request={
                "command_id":
                    (
                        "323e4567-e89b-12d3-a456-"
                        "426614174000"
                    ),
            },

            action_state=
                result,
        )

        self.assertFalse(
            linkage[
                "linked"
            ]
        )


if __name__ == "__main__":
    unittest.main()
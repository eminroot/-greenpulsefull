import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.hardware_ack_state import (
    normalize_real_ack_claim,
    normalize_simulated_ack,
)

from src.hardware_action_audit import (
    AUDIT_SCHEMA_VERSION,
    get_action_state_by_command_id,
    get_recent_action_states,
    initialize_action_state_audit,
    store_action_state,
)


COMMAND_ID = (
    "123e4567-e89b-12d3-a456-426614174000"
)

OBSERVATION_ID = (
    "223e4567-e89b-12d3-a456-426614174000"
)


def simulated_state():

    return normalize_simulated_ack(
        {
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
                "SIMULATED_EXECUTED",

            "error_code":
                None,

            "timestamp":
                "2026-09-24T12:00:00+00:00",

            "simulated":
                True,

            "physical_actuation":
                False,

            "real_hardware_ack":
                None,
        }
    )


class TestHardwareActionAudit(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            AUDIT_SCHEMA_VERSION,
            (
                "greenpulse."
                "hardware_action_state_audit.v1"
            ),
        )


    def test_initialize_creates_table(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            initialize_action_state_audit(
                db
            )

            conn = sqlite3.connect(db)

            try:

                row = conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                      AND name='hardware_action_states'
                    """
                ).fetchone()

            finally:

                conn.close()

        self.assertIsNotNone(
            row
        )


    def test_simulated_state_can_be_stored(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            stored = store_action_state(
                simulated_state(),
                db_path=db,
            )

            self.assertEqual(
                stored,
                COMMAND_ID,
            )


    def test_duplicate_command_id_not_overwritten(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_action_state(
                simulated_state(),
                db_path=db,
            )

            with self.assertRaises(
                sqlite3.IntegrityError
            ):

                store_action_state(
                    simulated_state(),
                    db_path=db,
                )


    def test_recent_action_state_readback(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_action_state(
                simulated_state(),
                db_path=db,
            )

            rows = get_recent_action_states(
                db_path=db,
            )

        self.assertEqual(
            len(rows),
            1,
        )

        self.assertEqual(
            rows[0][
                "action_state"
            ],
            "EXECUTED",
        )

        self.assertEqual(
            rows[0][
                "audit"
            ][
                "schema_version"
            ],
            AUDIT_SCHEMA_VERSION,
        )


    def test_read_by_command_id(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_action_state(
                simulated_state(),
                db_path=db,
            )

            result = (
                get_action_state_by_command_id(
                    COMMAND_ID,
                    db_path=db,
                )
            )

        self.assertEqual(
            result[
                "command_id"
            ],
            COMMAND_ID,
        )


    def test_missing_database_returns_empty(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "missing.db"

            rows = get_recent_action_states(
                db_path=db,
            )

        self.assertEqual(
            rows,
            [],
        )


    def test_simulated_state_remains_simulated_after_audit(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_action_state(
                simulated_state(),
                db_path=db,
            )

            result = (
                get_action_state_by_command_id(
                    COMMAND_ID,
                    db_path=db,
                )
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

        self.assertFalse(
            result[
                "physical_actuation"
            ]
        )


    def test_unverified_real_claim_can_be_audited_but_not_validated(self):

        real_claim = normalize_real_ack_claim(
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
                    "UNVERIFIED_CONTROLLER_ERROR",

                "timestamp":
                    "2026-09-24T12:00:00+00:00",
            }
        )

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_action_state(
                real_claim,
                db_path=db,
            )

            result = (
                get_action_state_by_command_id(
                    COMMAND_ID,
                    db_path=db,
                )
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


    def test_physical_actuation_true_rejected(self):

        state = simulated_state()

        state[
            "physical_actuation"
        ] = True

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            with self.assertRaises(
                ValueError
            ):

                store_action_state(
                    state,
                    db_path=db,
                )


if __name__ == "__main__":
    unittest.main()
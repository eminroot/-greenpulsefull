import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.closed_loop_intelligence import (
    build_followup_plan,
)

from src.closed_loop_followup_scheduler import (
    SCHEDULER_SCHEMA_VERSION,
    get_pending_followups,
    initialize_followup_scheduler,
    mark_followup_consumed,
    schedule_followup,
)


COMMAND_ID = (
    "123e4567-e89b-12d3-a456-426614174000"
)


def action(
    *,
    simulated=True,
    verified=False,
    physical=False,
):

    return {
        "schema_version":
            "greenpulse.hardware_action_state.v1",

        "command_id":
            COMMAND_ID,

        "observation_id":
            "OBS-ACTION",

        "plant_id":
            "P01",

        "action_state":
            "EXECUTED",

        "state_timestamp":
            "2026-09-24T12:05:00+00:00",

        "simulated":
            simulated,

        "real_hardware_ack_validated":
            verified,

        "physical_actuation":
            physical,
    }


def synthetic_plan():

    return build_followup_plan(
        action_state=
            action(),

        delay_seconds=
            600,

        test_only=
            True,
    )


class TestClosedLoopFollowupScheduler(
    unittest.TestCase
):

    def test_scheduler_schema_version(self):

        self.assertEqual(
            SCHEDULER_SCHEMA_VERSION,
            (
                "greenpulse."
                "closed_loop_followup_scheduler.v1"
            ),
        )


    def test_initialize_creates_schedule_table(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            initialize_followup_scheduler(
                db
            )

            conn = sqlite3.connect(
                db
            )

            try:

                row = conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                      AND name='closed_loop_followup_schedule'
                    """
                ).fetchone()

            finally:

                conn.close()


        self.assertIsNotNone(
            row
        )


    def test_synthetic_followup_can_be_scheduled(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            result = schedule_followup(
                synthetic_plan(),
                db_path=db,
            )


        self.assertTrue(
            result[
                "scheduled"
            ]
        )

        self.assertEqual(
            result[
                "schedule_state"
            ],
            "PENDING",
        )

        self.assertTrue(
            result[
                "test_only"
            ]
        )


    def test_duplicate_command_schedule_blocked(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            schedule_followup(
                synthetic_plan(),
                db_path=db,
            )

            with self.assertRaises(
                sqlite3.IntegrityError
            ):

                schedule_followup(
                    synthetic_plan(),
                    db_path=db,
                )


    def test_pending_queue_readback(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            schedule_followup(
                synthetic_plan(),
                db_path=db,
            )

            pending = get_pending_followups(
                db_path=db,
            )


        self.assertEqual(
            len(
                pending
            ),
            1,
        )

        self.assertEqual(
            pending[0][
                "command_id"
            ],
            COMMAND_ID,
        )


    def test_consumed_followup_removed_from_pending(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            schedule_followup(
                synthetic_plan(),
                db_path=db,
            )

            changed = mark_followup_consumed(
                COMMAND_ID,
                db_path=db,
            )

            pending = get_pending_followups(
                db_path=db,
            )


        self.assertTrue(
            changed
        )

        self.assertEqual(
            pending,
            [],
        )


    def test_scheduler_does_not_execute_inference(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            result = schedule_followup(
                synthetic_plan(),
                db_path=db,
            )


        self.assertFalse(
            result[
                "scheduler_executes_inference"
            ]
        )


    def test_scheduler_does_not_dispatch_hardware(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            result = schedule_followup(
                synthetic_plan(),
                db_path=db,
            )


        self.assertFalse(
            result[
                "scheduler_dispatches_hardware"
            ]
        )

        self.assertFalse(
            result[
                "physical_action_triggered"
            ]
        )


    def test_unverified_operational_plan_cannot_be_scheduled(self):

        blocked_plan = {
            "schema_version":
                "greenpulse.closed_loop_followup_plan.v1",

            "status":
                "FOLLOWUP_PLANNED",

            "command_id":
                COMMAND_ID,

            "plant_id":
                "P01",

            "action_timestamp":
                "2026-09-24T12:05:00+00:00",

            "delay_seconds":
                600.0,

            "followup_due_at":
                "2026-09-24T12:15:00+00:00",

            "test_only":
                False,

            "real_intervention_verified":
                False,
        }


        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            with self.assertRaises(
                ValueError
            ):

                schedule_followup(
                    blocked_plan,
                    db_path=db,
                )


    def test_verified_operational_plan_structure_can_queue(self):

        verified_action = action(
            simulated=False,
            verified=True,
            physical=True,
        )

        plan = build_followup_plan(
            action_state=
                verified_action,

            delay_seconds=
                600,

            test_only=
                False,
        )


        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            result = schedule_followup(
                plan,
                db_path=db,
            )


        self.assertFalse(
            result[
                "test_only"
            ]
        )

        self.assertTrue(
            result[
                "real_intervention_verified"
            ]
        )

        self.assertFalse(
            result[
                "physical_action_triggered"
            ]
        )


if __name__ == "__main__":
    unittest.main()
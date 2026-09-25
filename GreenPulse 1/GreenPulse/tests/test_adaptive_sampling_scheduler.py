import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.adaptive_sampling import (
    evaluate_adaptive_sampling,
)

from src.adaptive_sampling_scheduler import (
    SCHEDULER_SCHEMA_VERSION,
    get_pending_sampling_schedule,
    initialize_sampling_scheduler,
    mark_sampling_schedule_consumed,
    schedule_sampling_decision,
)


def decision(
    observation_id="OBS-001",
    *,
    risk=80.0,
    plant_id="P01",
):

    return evaluate_adaptive_sampling(
        {
            "plant_id":
                plant_id,

            "observation_id":
                observation_id,

            "timestamp":
                "2026-09-24T12:00:00+00:00",

            "risk_score":
                risk,

            "forecast_risk_score":
                None,

            "trend_state":
                None,

            "stable_healthy_confirmed":
                False,
        }
    )


class TestAdaptiveSamplingScheduler(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEDULER_SCHEMA_VERSION,
            "greenpulse.adaptive_sampling_scheduler.v1",
        )


    def test_table_creation(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            initialize_sampling_scheduler(
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
                      AND name='adaptive_sampling_schedule'
                    """
                ).fetchone()

            finally:

                conn.close()


        self.assertIsNotNone(
            row
        )


    def test_sampling_decision_can_be_scheduled(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            result = schedule_sampling_decision(
                item,
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


    def test_new_decision_supersedes_old_pending_schedule(self):

        first = decision(
            "OBS-001",
            risk=80.0,
        )

        second = decision(
            "OBS-002",
            risk=20.0,
        )


        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            schedule_sampling_decision(
                first,
                db_path=db,
            )

            schedule_sampling_decision(
                second,
                db_path=db,
            )

            pending = get_pending_sampling_schedule(
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
                "decision_id"
            ],
            second[
                "decision_id"
            ],
        )


    def test_different_plants_keep_independent_schedules(self):

        first = decision(
            "OBS-A",
            plant_id="P01",
        )

        second = decision(
            "OBS-B",
            plant_id="P02",
        )


        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            schedule_sampling_decision(
                first,
                db_path=db,
            )

            schedule_sampling_decision(
                second,
                db_path=db,
            )

            pending = get_pending_sampling_schedule(
                db_path=db,
            )


        self.assertEqual(
            len(
                pending
            ),
            2,
        )


    def test_next_observation_timestamp_preserved(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            result = schedule_sampling_decision(
                item,
                db_path=db,
            )


        self.assertEqual(
            result[
                "next_observation_at"
            ],
            item[
                "next_observation_at"
            ],
        )


    def test_consumed_schedule_leaves_pending_queue(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            schedule_sampling_decision(
                item,
                db_path=db,
            )

            changed = mark_sampling_schedule_consumed(
                item[
                    "decision_id"
                ],
                db_path=db,
            )

            pending = get_pending_sampling_schedule(
                db_path=db,
            )


        self.assertTrue(
            changed
        )

        self.assertEqual(
            pending,
            [],
        )


    def test_duplicate_decision_id_is_blocked(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            schedule_sampling_decision(
                item,
                db_path=db,
            )


            with self.assertRaises(
                sqlite3.IntegrityError
            ):

                schedule_sampling_decision(
                    item,
                    db_path=db,
                )


    def test_scheduler_never_triggers_camera(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            result = schedule_sampling_decision(
                item,
                db_path=db,
            )


        self.assertFalse(
            result[
                "camera_triggered"
            ]
        )

        self.assertFalse(
            result[
                "image_captured"
            ]
        )


    def test_scheduler_never_triggers_inference(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            result = schedule_sampling_decision(
                item,
                db_path=db,
            )


        self.assertFalse(
            result[
                "inference_triggered"
            ]
        )


    def test_development_policy_status_is_preserved(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "schedule.db"

            schedule_sampling_decision(
                item,
                db_path=db,
            )

            pending = get_pending_sampling_schedule(
                db_path=db,
            )


        self.assertEqual(
            pending[0][
                "policy_status"
            ],
            "DEVELOPMENT_ONLY_UNVALIDATED",
        )


if __name__ == "__main__":
    unittest.main()
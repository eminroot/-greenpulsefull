import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.adaptive_sampling import (
    evaluate_adaptive_sampling,
)

from src.adaptive_sampling_audit import (
    AUDIT_SCHEMA_VERSION,
    get_recent_sampling_decisions,
    get_sampling_decision,
    initialize_sampling_audit,
    store_sampling_decision,
)


def decision():

    return evaluate_adaptive_sampling(
        {
            "plant_id":
                "P01",

            "observation_id":
                "OBS-001",

            "timestamp":
                "2026-09-24T12:00:00+00:00",

            "risk_score":
                80.0,

            "forecast_risk_score":
                75.0,

            "trend_state":
                "RISING",

            "stable_healthy_confirmed":
                False,
        }
    )


class TestAdaptiveSamplingAudit(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            AUDIT_SCHEMA_VERSION,
            "greenpulse.adaptive_sampling_audit.v1",
        )


    def test_table_creation(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            initialize_sampling_audit(
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
                      AND name='adaptive_sampling_decisions'
                    """
                ).fetchone()

            finally:

                conn.close()


        self.assertIsNotNone(
            row
        )


    def test_decision_can_be_stored(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            stored = store_sampling_decision(
                item,
                db_path=db,
            )


        self.assertEqual(
            stored,
            item[
                "decision_id"
            ],
        )


    def test_duplicate_decision_not_overwritten(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_sampling_decision(
                item,
                db_path=db,
            )


            with self.assertRaises(
                sqlite3.IntegrityError
            ):

                store_sampling_decision(
                    item,
                    db_path=db,
                )


    def test_recent_readback(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_sampling_decision(
                item,
                db_path=db,
            )

            rows = get_recent_sampling_decisions(
                db_path=db,
            )


        self.assertEqual(
            len(
                rows
            ),
            1,
        )

        self.assertEqual(
            rows[0][
                "sampling_level"
            ],
            "HIGH",
        )


    def test_read_by_decision_id(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_sampling_decision(
                item,
                db_path=db,
            )

            result = get_sampling_decision(
                item[
                    "decision_id"
                ],
                db_path=db,
            )


        self.assertEqual(
            result[
                "decision_id"
            ],
            item[
                "decision_id"
            ],
        )


    def test_reason_codes_preserved(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_sampling_decision(
                item,
                db_path=db,
            )

            result = get_sampling_decision(
                item[
                    "decision_id"
                ],
                db_path=db,
            )


        self.assertIn(
            "HIGH_CURRENT_RISK",
            result[
                "reason_codes"
            ],
        )


    def test_policy_version_preserved(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_sampling_decision(
                item,
                db_path=db,
            )

            result = get_sampling_decision(
                item[
                    "decision_id"
                ],
                db_path=db,
            )


        self.assertEqual(
            result[
                "policy_version"
            ],
            "1.0.0-development",
        )


    def test_missing_database_returns_empty(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "missing.db"

            rows = get_recent_sampling_decisions(
                db_path=db,
            )


        self.assertEqual(
            rows,
            [],
        )


    def test_unvalidated_policy_status_preserved(self):

        item = decision()

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_sampling_decision(
                item,
                db_path=db,
            )

            result = get_sampling_decision(
                item[
                    "decision_id"
                ],
                db_path=db,
            )


        self.assertEqual(
            result[
                "policy_status"
            ],
            "DEVELOPMENT_ONLY_UNVALIDATED",
        )


if __name__ == "__main__":
    unittest.main()
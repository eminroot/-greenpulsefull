import sqlite3
import unittest

from src.data_logging_audit import (
    REQUIRED_TABLES,
    SCHEMA_VERSION,
    audit_schema,
    initialize_audit_schema,
)


class TestDataLoggingAudit(
    unittest.TestCase
):

    def setUp(self):

        self.conn = sqlite3.connect(
            ":memory:"
        )

        initialize_audit_schema(
            self.conn
        )


    def tearDown(self):

        self.conn.close()


    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.data_logging_audit.v1",
        )


    def test_exact_required_table_count(self):

        self.assertEqual(
            len(
                REQUIRED_TABLES
            ),
            12,
        )


    def test_all_required_tables_created(self):

        result = audit_schema(
            self.conn
        )

        self.assertTrue(
            result[
                "all_required_tables_present"
            ]
        )

        self.assertEqual(
            result[
                "present_required_table_count"
            ],
            12,
        )


    def test_no_required_tables_missing(self):

        result = audit_schema(
            self.conn
        )

        self.assertEqual(
            result[
                "missing_tables"
            ],
            [],
        )


    def test_foreign_keys_enabled(self):

        result = audit_schema(
            self.conn
        )

        self.assertTrue(
            result[
                "foreign_keys_enabled"
            ]
        )


    def test_initialization_is_idempotent(self):

        initialize_audit_schema(
            self.conn
        )

        result = audit_schema(
            self.conn
        )

        self.assertTrue(
            result[
                "all_required_tables_present"
            ]
        )


    def test_duplicate_command_id_rejected(self):

        self._insert_lineage_fixture()

        with self.assertRaises(
            sqlite3.IntegrityError
        ):

            self.conn.execute(
                """
                INSERT INTO commands (
                    command_id,
                    observation_id,
                    decision_id,
                    command_type,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "CMD-001",
                    "OBS-001",
                    "DEC-001",
                    "IRRIGATION_REQUEST",
                    "{}",
                    "2026-09-24T00:00:10Z",
                ),
            )


    def test_invalid_command_foreign_key_rejected(self):

        with self.assertRaises(
            sqlite3.IntegrityError
        ):

            self.conn.execute(
                """
                INSERT INTO commands (
                    command_id,
                    observation_id,
                    decision_id,
                    command_type,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "CMD-BAD",
                    "OBS-MISSING",
                    "DEC-MISSING",
                    "TEST",
                    "{}",
                    "2026-09-24T00:00:00Z",
                ),
            )


    def _insert_lineage_fixture(self):

        self.conn.execute(
            """
            INSERT INTO observations
            VALUES (?, ?, ?, ?)
            """,
            (
                "OBS-001",
                "2026-09-24T00:00:00Z",
                "PLANT-001",
                "tomato",
            ),
        )

        self.conn.execute(
            """
            INSERT INTO model_versions
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "MODEL-001",
                "test-model",
                "abc123",
                "models/test.onnx",
                "2026-09-24T00:00:00Z",
            ),
        )

        self.conn.execute(
            """
            INSERT INTO risk_scores
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "RISK-001",
                "OBS-001",
                "MODEL-001",
                50.0,
                "2026-09-24T00:00:02Z",
            ),
        )

        self.conn.execute(
            """
            INSERT INTO forecasts
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "FOR-001",
                "OBS-001",
                "MODEL-001",
                "{}",
                "2026-09-24T00:00:03Z",
            ),
        )

        self.conn.execute(
            """
            INSERT INTO decisions
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "DEC-001",
                "OBS-001",
                "RISK-001",
                "FOR-001",
                "MONITOR",
                "{}",
                "2026-09-24T00:00:04Z",
            ),
        )

        self.conn.execute(
            """
            INSERT INTO commands
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "CMD-001",
                "OBS-001",
                "DEC-001",
                "TEST_COMMAND",
                "{}",
                "2026-09-24T00:00:05Z",
            ),
        )


if __name__ == "__main__":
    unittest.main()
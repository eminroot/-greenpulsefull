import sqlite3
import unittest

from src.audit_traceability import (
    SCHEMA_VERSION,
    trace_command,
)

from src.data_logging_audit import (
    initialize_audit_schema,
)


class TestAuditTraceability(
    unittest.TestCase
):

    def setUp(self):

        self.conn = sqlite3.connect(
            ":memory:"
        )

        initialize_audit_schema(
            self.conn
        )

        self._insert_fixture()


    def tearDown(self):

        self.conn.close()


    def _insert_fixture(self):

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
                "vision-test",
                "sha-test",
                "models/test.onnx",
                "2026-09-24T00:00:00Z",
            ),
        )

        self.conn.execute(
            """
            INSERT INTO images
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "IMG-001",
                "OBS-001",
                "data/test.jpg",
                "image-sha",
                "2026-09-24T00:00:00Z",
            ),
        )

        self.conn.execute(
            """
            INSERT INTO predictions
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "PRED-001",
                "OBS-001",
                "IMG-001",
                "MODEL-001",
                "healthy",
                0.99,
                "2026-09-24T00:00:01Z",
            ),
        )

        self.conn.execute(
            """
            INSERT INTO sensor_readings
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "SENSORREAD-001",
                "OBS-001",
                "SENSOR-001",
                "soil_moisture",
                42.0,
                "percent",
                "2026-09-24T00:00:01Z",
                "VALID",
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
                22.5,
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
                '{"trend":"stable"}',
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
                '["TEST_ONLY"]',
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

        self.conn.execute(
            """
            INSERT INTO actions
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "ACT-001",
                "CMD-001",
                "SIMULATED",
                "SIMULATED_ACK",
                "2026-09-24T00:00:06Z",
            ),
        )

        self.conn.commit()


    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.command_trace.v1",
        )


    def test_trace_returns_observation(self):

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertEqual(
            trace[
                "observation"
            ][
                "observation_id"
            ],
            "OBS-001",
        )


    def test_trace_returns_image(self):

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertEqual(
            trace[
                "images"
            ][
                0
            ][
                "image_id"
            ],
            "IMG-001",
        )


    def test_trace_returns_sensor_data(self):

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertEqual(
            trace[
                "sensor_readings"
            ][
                0
            ][
                "sensor_reading_id"
            ],
            "SENSORREAD-001",
        )


    def test_trace_returns_model_version(self):

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertEqual(
            trace[
                "model_versions"
            ][
                0
            ][
                "model_version_id"
            ],
            "MODEL-001",
        )


    def test_trace_returns_risk_score(self):

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertEqual(
            trace[
                "risk_scores"
            ][
                0
            ][
                "risk_score_id"
            ],
            "RISK-001",
        )


    def test_trace_returns_forecast(self):

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertEqual(
            trace[
                "forecasts"
            ][
                0
            ][
                "forecast_id"
            ],
            "FOR-001",
        )


    def test_trace_returns_decision(self):

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertEqual(
            trace[
                "decision"
            ][
                "decision_id"
            ],
            "DEC-001",
        )


    def test_required_lineage_complete(self):

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertTrue(
            trace[
                "required_lineage_complete"
            ]
        )


    def test_unknown_command_rejected(self):

        with self.assertRaises(
            KeyError
        ):

            trace_command(
                self.conn,
                "CMD-UNKNOWN",
            )


if __name__ == "__main__":
    unittest.main()
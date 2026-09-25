import copy
import sqlite3
import unittest

from src.audit_traceability import (
    trace_command,
)

from src.data_logging_audit import (
    initialize_audit_schema,
)

from src.data_logging_writer import (
    SCHEMA_VERSION,
    write_audit_bundle,
)


def make_bundle(
    suffix="001",
):

    obs = f"OBS-{suffix}"
    img = f"IMG-{suffix}"
    pred = f"PRED-{suffix}"
    sensor = f"SENSORREAD-{suffix}"
    risk = f"RISK-{suffix}"
    forecast = f"FOR-{suffix}"
    decision = f"DEC-{suffix}"
    command = f"CMD-{suffix}"
    action = f"ACT-{suffix}"
    metric = f"MET-{suffix}"
    event = f"EVT-{suffix}"


    return {
        "observation": {
            "observation_id":
                obs,

            "timestamp":
                "2026-09-24T00:00:00Z",

            "plant_id":
                "PLANT-001",

            "crop":
                "tomato",
        },

        "model_versions": [
            {
                "model_version_id":
                    "MODEL-001",

                "model_name":
                    "test-model",

                "model_sha256":
                    "abc123",

                "artifact_path":
                    "models/test.onnx",

                "created_at":
                    "2026-09-24T00:00:00Z",
            }
        ],

        "images": [
            {
                "image_id":
                    img,

                "observation_id":
                    obs,

                "image_path":
                    f"data/{img}.jpg",

                "image_sha256":
                    "image-sha",

                "captured_at":
                    "2026-09-24T00:00:00Z",
            }
        ],

        "predictions": [
            {
                "prediction_id":
                    pred,

                "observation_id":
                    obs,

                "image_id":
                    img,

                "model_version_id":
                    "MODEL-001",

                "predicted_class":
                    "healthy",

                "confidence":
                    0.99,

                "created_at":
                    "2026-09-24T00:00:01Z",
            }
        ],

        "sensor_readings": [
            {
                "sensor_reading_id":
                    sensor,

                "observation_id":
                    obs,

                "sensor_id":
                    "SENSOR-001",

                "sensor_type":
                    "soil_moisture",

                "value":
                    42.0,

                "unit":
                    "percent",

                "timestamp":
                    "2026-09-24T00:00:01Z",

                "validation_status":
                    "VALID",
            }
        ],

        "risk_scores": [
            {
                "risk_score_id":
                    risk,

                "observation_id":
                    obs,

                "model_version_id":
                    "MODEL-001",

                "risk_score":
                    22.5,

                "created_at":
                    "2026-09-24T00:00:02Z",
            }
        ],

        "forecasts": [
            {
                "forecast_id":
                    forecast,

                "observation_id":
                    obs,

                "model_version_id":
                    "MODEL-001",

                "forecast_json":
                    '{"trend":"stable"}',

                "created_at":
                    "2026-09-24T00:00:03Z",
            }
        ],

        "decision": {
            "decision_id":
                decision,

            "observation_id":
                obs,

            "risk_score_id":
                risk,

            "forecast_id":
                forecast,

            "decision":
                "MONITOR",

            "reason_json":
                '["TEST_ONLY"]',

            "created_at":
                "2026-09-24T00:00:04Z",
        },

        "command": {
            "command_id":
                command,

            "observation_id":
                obs,

            "decision_id":
                decision,

            "command_type":
                "TEST_COMMAND",

            "payload_json":
                "{}",

            "created_at":
                "2026-09-24T00:00:05Z",
        },

        "actions": [
            {
                "action_id":
                    action,

                "command_id":
                    command,

                "action_state":
                    "SIMULATED",

                "ack_type":
                    "SIMULATED_ACK",

                "created_at":
                    "2026-09-24T00:00:06Z",
            }
        ],

        "sustainability_metrics": [
            {
                "metric_id":
                    metric,

                "observation_id":
                    obs,

                "command_id":
                    command,

                "metric_name":
                    "TEST_ONLY_METRIC",

                "metric_value":
                    0.0,

                "metric_unit":
                    "test",

                "created_at":
                    "2026-09-24T00:00:07Z",
            }
        ],

        "system_events": [
            {
                "event_id":
                    event,

                "observation_id":
                    obs,

                "command_id":
                    command,

                "event_type":
                    "TEST_EVENT",

                "severity":
                    "INFO",

                "payload_json":
                    "{}",

                "created_at":
                    "2026-09-24T00:00:08Z",
            }
        ],
    }


class TestDataLoggingWriter(
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
            "greenpulse.audit_writer.v1",
        )


    def test_complete_bundle_written(self):

        result = write_audit_bundle(
            self.conn,
            make_bundle(),
        )

        self.assertEqual(
            result[
                "command_id"
            ],
            "CMD-001",
        )

        self.assertTrue(
            result[
                "atomic_write"
            ]
        )


    def test_trace_complete_after_write(self):

        write_audit_bundle(
            self.conn,
            make_bundle(),
        )

        trace = trace_command(
            self.conn,
            "CMD-001",
        )

        self.assertTrue(
            trace[
                "required_lineage_complete"
            ]
        )


    def test_multiple_sensor_readings_supported(self):

        bundle = make_bundle()

        bundle[
            "sensor_readings"
        ].append(
            {
                "sensor_reading_id":
                    "SENSORREAD-002",

                "observation_id":
                    "OBS-001",

                "sensor_id":
                    "SENSOR-002",

                "sensor_type":
                    "temperature",

                "value":
                    25.0,

                "unit":
                    "C",

                "timestamp":
                    "2026-09-24T00:00:01Z",

                "validation_status":
                    "VALID",
            }
        )


        write_audit_bundle(
            self.conn,
            bundle,
        )


        count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM sensor_readings
            """
        ).fetchone()[0]


        self.assertEqual(
            count,
            2,
        )


    def test_optional_audit_rows_persist(self):

        write_audit_bundle(
            self.conn,
            make_bundle(),
        )


        action_count = self.conn.execute(
            "SELECT COUNT(*) FROM actions"
        ).fetchone()[0]

        metric_count = self.conn.execute(
            "SELECT COUNT(*) FROM sustainability_metrics"
        ).fetchone()[0]

        event_count = self.conn.execute(
            "SELECT COUNT(*) FROM system_events"
        ).fetchone()[0]


        self.assertEqual(
            (
                action_count,
                metric_count,
                event_count,
            ),
            (
                1,
                1,
                1,
            ),
        )


    def test_input_bundle_not_mutated(self):

        bundle = make_bundle()

        original = copy.deepcopy(
            bundle
        )


        result = write_audit_bundle(
            self.conn,
            bundle,
        )


        self.assertEqual(
            bundle,
            original,
        )

        self.assertFalse(
            result[
                "input_mutated"
            ]
        )


    def test_invalid_observation_link_rejected_atomically(self):

        bundle = make_bundle()

        bundle[
            "sensor_readings"
        ][0][
            "observation_id"
        ] = "OBS-WRONG"


        with self.assertRaises(
            ValueError
        ):

            write_audit_bundle(
                self.conn,
                bundle,
            )


        count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM observations
            """
        ).fetchone()[0]


        self.assertEqual(
            count,
            0,
        )


    def test_duplicate_bundle_rejected_without_extra_rows(self):

        bundle = make_bundle()

        write_audit_bundle(
            self.conn,
            bundle,
        )


        before = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM observations
            """
        ).fetchone()[0]


        with self.assertRaises(
            sqlite3.IntegrityError
        ):

            write_audit_bundle(
                self.conn,
                bundle,
            )


        after = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM observations
            """
        ).fetchone()[0]


        self.assertEqual(
            before,
            after,
        )


    def test_existing_identical_model_version_reused(self):

        write_audit_bundle(
            self.conn,
            make_bundle(
                "001"
            ),
        )

        write_audit_bundle(
            self.conn,
            make_bundle(
                "002"
            ),
        )


        model_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM model_versions
            """
        ).fetchone()[0]


        observation_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM observations
            """
        ).fetchone()[0]


        self.assertEqual(
            model_count,
            1,
        )

        self.assertEqual(
            observation_count,
            2,
        )


    def test_conflicting_model_version_rejected(self):

        write_audit_bundle(
            self.conn,
            make_bundle(
                "001"
            ),
        )


        bundle = make_bundle(
            "002"
        )

        bundle[
            "model_versions"
        ][0][
            "model_sha256"
        ] = "DIFFERENT-SHA"


        with self.assertRaises(
            ValueError
        ):

            write_audit_bundle(
                self.conn,
                bundle,
            )


        observation_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM observations
            """
        ).fetchone()[0]


        self.assertEqual(
            observation_count,
            1,
        )


if __name__ == "__main__":
    unittest.main()
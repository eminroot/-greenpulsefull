import ast
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.ai_gateway_service import (
    GATEWAY_SCHEMA_VERSION,
    get_model_registry_info,
    get_recent_event_view,
    get_recent_sensor_view,
)


def create_database(
    path,
):

    conn = sqlite3.connect(
        path
    )

    try:

        conn.execute(
            """
            CREATE TABLE observations (
                observation_id TEXT,
                timestamp TEXT,
                plant_id TEXT,
                crop TEXT,
                image_sha256 TEXT,
                predicted_class TEXT,
                sensor_status TEXT,
                time_sync_status TEXT,
                decision TEXT,
                model_sha256 TEXT,
                response_json TEXT
            )
            """
        )


        observations = [
            {
                "schema_version":
                    "0.6.0",

                "observation_id":
                    "OBS-2",

                "timestamp":
                    "2026-09-24T10:01:00+00:00",

                "plant_id":
                    "P02",

                "crop":
                    "tomato",

                "sensor": {
                    "status":
                        "VALID",

                    "reason":
                        "all_checks_passed",

                    "data": {
                        "plant_id":
                            "P02",
                    },
                },

                "decision": {
                    "action":
                        "NO_AUTONOMOUS_ACTION",

                    "reason_codes": [
                        "WATER_STRESS_MODEL_NOT_VALIDATED"
                    ],
                },
            },
            {
                "schema_version":
                    "0.6.0",

                "observation_id":
                    "OBS-1",

                "timestamp":
                    "2026-09-24T10:00:00+00:00",

                "plant_id":
                    "P01",

                "crop":
                    "tomato",

                "sensor": {
                    "status":
                        "VALID_SIMULATED",

                    "reason":
                        "simulation_only",

                    "data": {
                        "plant_id":
                            "P01",
                    },
                },

                "decision": {
                    "action":
                        "NO_AUTONOMOUS_ACTION",

                    "reason_codes": [
                        "SENSOR_SIMULATED"
                    ],
                },
            },
        ]


        for item in observations:

            conn.execute(
                """
                INSERT INTO observations
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item[
                        "observation_id"
                    ],
                    item[
                        "timestamp"
                    ],
                    item[
                        "plant_id"
                    ],
                    item[
                        "crop"
                    ],
                    "image-sha",
                    None,
                    item[
                        "sensor"
                    ][
                        "status"
                    ],
                    "SYNCED",
                    item[
                        "decision"
                    ][
                        "action"
                    ],
                    "model-sha",
                    json.dumps(
                        item
                    ),
                ),
            )

        conn.commit()

    finally:

        conn.close()


class TestAIGatewayService(
    unittest.TestCase
):

    def test_service_has_versioned_contract(self):

        self.assertEqual(
            GATEWAY_SCHEMA_VERSION,
            "greenpulse.ai_gateway_service.v1",
        )


    def test_missing_database_returns_empty_events(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = get_recent_event_view(
                database_path=
                    Path(tmp)
                    / "missing.db",
            )

        self.assertEqual(
            result[
                "count"
            ],
            0,
        )


    def test_events_are_read_from_audit_log(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = (
                Path(tmp)
                / "test.db"
            )

            create_database(
                db
            )

            result = get_recent_event_view(
                database_path=db,
            )

        self.assertEqual(
            result[
                "count"
            ],
            2,
        )

        self.assertEqual(
            result[
                "events"
            ][0][
                "observation_id"
            ],
            "OBS-1",
        )


    def test_event_view_never_claims_physical_action(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = (
                Path(tmp)
                / "test.db"
            )

            create_database(
                db
            )

            result = get_recent_event_view(
                database_path=db,
            )

        self.assertFalse(
            result[
                "physical_actuation"
            ]
        )


    def test_sensor_view_can_filter_plant(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = (
                Path(tmp)
                / "test.db"
            )

            create_database(
                db
            )

            result = get_recent_sensor_view(
                plant_id=
                    "P01",

                database_path=
                    db,
            )

        self.assertEqual(
            result[
                "count"
            ],
            1,
        )

        self.assertEqual(
            result[
                "sensors"
            ][0][
                "plant_id"
            ],
            "P01",
        )


    def test_sensor_source_is_not_authentication(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = (
                Path(tmp)
                / "test.db"
            )

            create_database(
                db
            )

            result = get_recent_sensor_view(
                database_path=db,
            )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "source_field_is_device_authentication"
            ]
        )


    def test_registry_info_does_not_claim_operational_release(self):

        with tempfile.TemporaryDirectory() as tmp:

            registry = (
                Path(tmp)
                / "registry.json"
            )

            registry.write_text(
                json.dumps(
                    {
                        "version":
                            "1.0",

                        "mode":
                            "RESEARCH_ONLY",

                        "crop_identity_source":
                            "UNVERIFIED_EXTERNAL_CLAIM",

                        "unknown_crop_policy":
                            "ABSTAIN",

                        "actuation_authorized":
                            False,

                        "models": {
                            "tomato": {
                                "crop":
                                    "tomato",

                                "class_count":
                                    1,

                                "class_names": [
                                    "healthy"
                                ],

                                "pytorch": {
                                    "path":
                                        "hidden.pt",

                                    "sha256":
                                        "a" * 64,
                                },

                                "onnx": {
                                    "path":
                                        "hidden.onnx",

                                    "sha256":
                                        "b" * 64,
                                },

                                "operational_release_approved":
                                    False,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = get_model_registry_info(
                registry_path=
                    registry
            )

        self.assertEqual(
            result[
                "mode"
            ],
            "RESEARCH_ONLY",
        )

        self.assertFalse(
            result[
                "actuation_authorized"
            ]
        )

        serialized = json.dumps(
            result
        ).lower()

        self.assertNotIn(
            "pytorch_path",
            serialized,
        )

        self.assertNotIn(
            "onnx_path",
            serialized,
        )

        self.assertNotIn(
            "hidden.pt",
            serialized,
        )

        self.assertNotIn(
            "hidden.onnx",
            serialized,
        )


    def test_model_import_is_not_top_level(self):

        path = Path(
            "src/ai_gateway_service.py"
        )

        tree = ast.parse(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

        top_level_model_import = False

        for node in tree.body:

            if isinstance(
                node,
                ast.ImportFrom,
            ):

                if (
                    node.module
                    == "src.vision_inference"
                ):

                    top_level_model_import = True

        self.assertFalse(
            top_level_model_import
        )


if __name__ == "__main__":
    unittest.main()
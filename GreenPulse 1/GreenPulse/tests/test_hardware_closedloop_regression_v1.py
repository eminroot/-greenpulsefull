
import json
import sqlite3
import tempfile
import unittest

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator

from src.hardware_contract import (
    prepare_hardware_handoff
)

from src.actuator_simulator import simulate_actuator

from src.simulated_irrigation_flow import (
    run_simulated_irrigation_flow
)

from src.closed_loop_simulator import (
    run_simulated_closed_loop
)

from src.closed_loop_feedback_contract import (
    get_simulated_feedback
)


ROOT = Path(__file__).resolve().parents[1]


class GreenPulseHardwareRegression(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()

        self.addCleanup(
            self.temp.cleanup
        )

        self.db = (
            Path(self.temp.name) /
            "isolated_test.db"
        )

    def command(self):
        return {
            "command_id": str(uuid4()),
            "observation_id": str(uuid4()),
            "plant_id": "TEST-TOM-01",
            "mode": "SIMULATION_ONLY",
            "test_only": True,
            "origin": "TEST_HARNESS",
            "action": "IRRIGATION_TEST",
            "target": "MAIN_IRRIGATION_PUMP"
        }

    def fixture(self, plant_id="TEST-TOM-01"):
        now = datetime.now(timezone.utc)

        payload = {
            "mode": "SIMULATION_ONLY",
            "origin": "TEST_HARNESS",
            "test_only": True,
            "dataset_origin": "SYNTHETIC_FIXTURE",
            "plant_id": plant_id,
            "observation_id": str(uuid4()),
            "sensor_samples": [
                {
                    "timestamp": (
                        now - timedelta(minutes=3)
                    ).isoformat(),
                    "soil_moisture_pct": 27.0,
                    "source": "SIMULATED"
                },
                {
                    "timestamp": (
                        now - timedelta(minutes=2)
                    ).isoformat(),
                    "soil_moisture_pct": 26.0,
                    "source": "SIMULATED"
                },
                {
                    "timestamp": (
                        now - timedelta(minutes=1)
                    ).isoformat(),
                    "soil_moisture_pct": 25.0,
                    "source": "SIMULATED"
                }
            ]
        }

        followup = [
            {
                "timestamp": (
                    now + timedelta(minutes=2)
                ).isoformat(),
                "soil_moisture_pct": 29.0,
                "source": "SIMULATED"
            },
            {
                "timestamp": (
                    now + timedelta(minutes=4)
                ).isoformat(),
                "soil_moisture_pct": 33.0,
                "source": "SIMULATED"
            }
        ]

        return payload, followup

    def test_01_unauthorized_hardware_blocked(self):
        result = prepare_hardware_handoff({
            "observation_id": str(uuid4()),
            "plant_id": "TEST-TOM-01",
            "decision": {
                "action": "IRRIGATION_REQUEST",
                "reason_codes": []
            }
        })

        self.assertEqual(
            result["status"],
            "BLOCKED"
        )

        self.assertFalse(
            result["dispatch_permitted"]
        )

        self.assertIsNone(
            result["actuator_request"]
        )

    def test_02_operational_command_rejected(self):
        command = self.command()

        command["mode"] = "OPERATIONAL"
        command["test_only"] = False

        result = simulate_actuator(command)

        self.assertEqual(
            result["status"],
            "SIMULATED_REJECTED"
        )

        self.assertFalse(
            result["physical_actuation"]
        )

    def test_03_command_schema_is_strict(self):
        schema_path = (
            ROOT /
            "configs/actuator_schema_v1.json"
        )

        schema = json.loads(
            schema_path.read_text(
                encoding="utf-8-sig"
            )
        )

        validator = Draft202012Validator(
            schema
        )

        valid = self.command()

        self.assertTrue(
            validator.is_valid(valid)
        )

        invalid = {
            **valid,
            "unexpected_field": True
        }

        self.assertFalse(
            validator.is_valid(invalid)
        )

    def test_04_closed_loop_and_readback(self):
        payload, followup = self.fixture()

        result = run_simulated_closed_loop(
            payload,
            followup,
            db_path=self.db
        )

        self.assertTrue(
            result["feedback_recorded"]
        )

        feedback = get_simulated_feedback(
            result["command_id"],
            db_path=self.db
        )

        self.assertEqual(
            feedback["command_id"],
            result["command_id"]
        )

        self.assertEqual(
            feedback["synthetic_delta_pct_points"],
            8.0
        )

        self.assertFalse(
            feedback["physical_actuation"]
        )

        self.assertIsNone(
            feedback["measured_water_ml"]
        )

        self.assertIsNone(
            feedback["water_stress_risk_after"]
        )

    def test_05_database_cooldown(self):
        payload, _ = self.fixture()

        first = run_simulated_irrigation_flow(
            payload,
            db_path=self.db
        )

        self.assertEqual(
            first["simulated_ack"]["status"],
            "SIMULATED_EXECUTED"
        )

        repeated = run_simulated_irrigation_flow(
            {
                **payload,
                "observation_id": str(uuid4()),
                "seconds_since_last_simulated_action":
                    999999
            },
            db_path=self.db
        )

        self.assertIsNone(
            repeated["command"]
        )

        self.assertIn(
            "SIMULATED_COOLDOWN_ACTIVE",
            repeated["reason_codes"]
        )

    def test_06_pump_failure(self):
        payload, followup = self.fixture()

        result = run_simulated_closed_loop(
            payload,
            followup,
            scenario="FAILURE",
            db_path=self.db
        )

        self.assertFalse(
            result["feedback_recorded"]
        )

        self.assertEqual(
            result["actuator_status"],
            "SIMULATED_FAILED"
        )

    def test_07_controller_timeout(self):
        payload, followup = self.fixture()

        result = run_simulated_closed_loop(
            payload,
            followup,
            scenario="TIMEOUT",
            db_path=self.db
        )

        self.assertFalse(
            result["feedback_recorded"]
        )

        self.assertEqual(
            result["actuator_status"],
            "SIMULATED_TIMEOUT"
        )

    def test_08_operational_flow_rejected(self):
        payload, _ = self.fixture()

        payload["mode"] = "OPERATIONAL"
        payload["test_only"] = False

        result = run_simulated_irrigation_flow(
            payload,
            db_path=self.db
        )

        self.assertIsNone(
            result["command"]
        )

        self.assertFalse(
            result["physical_actuation"]
        )

        self.assertFalse(
            self.db.exists()
        )

    def test_09_real_source_not_accepted(self):
        payload, followup = self.fixture()

        followup[0]["source"] = "REAL"

        with self.assertRaises(ValueError):
            run_simulated_closed_loop(
                payload,
                followup,
                db_path=self.db
            )

        self.assertFalse(
            self.db.exists()
        )

    def test_10_tampered_feedback_rejected(self):
        payload, followup = self.fixture()

        result = run_simulated_closed_loop(
            payload,
            followup,
            db_path=self.db
        )

        command_id = result["command_id"]

        with closing(
            sqlite3.connect(self.db)
        ) as conn:
            with conn:
                conn.execute(
                    """
                    UPDATE simulated_followup_events
                    SET moisture_after_pct = 99
                    WHERE command_id = ?
                    """,
                    (command_id,)
                )

        with self.assertRaises(ValueError):
            get_simulated_feedback(
                command_id,
                db_path=self.db
            )


if __name__ == "__main__":
    unittest.main()

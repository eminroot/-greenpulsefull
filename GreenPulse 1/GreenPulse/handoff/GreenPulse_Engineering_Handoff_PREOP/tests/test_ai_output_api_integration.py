import unittest
from unittest.mock import patch
from pathlib import Path

from src.api import app, latest, plant_history
from src.ai_output_contract import SCHEMA_VERSION


def legacy_observation(
    observation_id="OBS-TEST-001",
    plant_id="P01",
):
    return {
        "schema_version": "0.6.0",
        "observation_id": observation_id,
        "timestamp": "2026-09-24T10:00:00+00:00",
        "plant_id": plant_id,
        "crop": "tomato",
        "vision": {
            "state": "VISUALLY_HEALTHY",
            "predicted_class": "Tomato___healthy",
            "confidence": 0.95,
        },
        "sensor": {
            "status": "VALID",
            "reason": "all_checks_passed",
            "data": {
                "plant_id": plant_id,
                "soil_moisture_pct": 50.0,
                "temperature_c": 25.0,
                "humidity_pct": 60.0,
            },
        },
        "water_stress_risk": None,
        "forecast": None,
        "decision": {
            "action": "NO_AUTONOMOUS_ACTION",
            "reason_codes": [
                "WATER_STRESS_MODEL_NOT_VALIDATED"
            ],
        },
        "model": {
            "version": "test-model-v1",
            "sha256": "test-sha",
        },
    }


class TestAIOutputAPIIntegration(unittest.TestCase):

    @patch("src.api.check_observation_freshness")
    @patch("src.api.get_latest_observation")
    def test_latest_standard_contract(
        self,
        mock_latest,
        mock_freshness,
    ):
        mock_latest.return_value = legacy_observation()
        mock_freshness.return_value = {
            "status": "FRESH"
        }

        result = latest()

        self.assertEqual(
            result["schema_version"],
            SCHEMA_VERSION,
        )

        self.assertEqual(
            result["observation_id"],
            "OBS-TEST-001",
        )


    @patch("src.api.check_observation_freshness")
    @patch("src.api.get_latest_observation")
    def test_latest_preserves_freshness(
        self,
        mock_latest,
        mock_freshness,
    ):
        mock_latest.return_value = legacy_observation()
        mock_freshness.return_value = {
            "status": "FRESH"
        }

        result = latest()

        self.assertEqual(
            result["observation_freshness"]["status"],
            "FRESH",
        )


    @patch("src.api.check_observation_freshness")
    @patch("src.api.get_plant_history")
    def test_history_standard_collection(
        self,
        mock_history,
        mock_freshness,
    ):
        mock_history.return_value = [
            legacy_observation("OBS-1", "P01"),
            legacy_observation("OBS-2", "P01"),
        ]

        mock_freshness.return_value = {
            "status": "FRESH"
        }

        result = plant_history(
            "P01",
            10,
        )

        self.assertEqual(
            result["schema_version"],
            "greenpulse.standard_ai_output_collection.v1",
        )

        self.assertEqual(
            result["count"],
            2,
        )

        self.assertTrue(
            all(
                item["schema_version"]
                == SCHEMA_VERSION
                for item
                in result["observations"]
            )
        )


    @patch("src.api.check_observation_freshness")
    @patch("src.api.get_plant_history")
    def test_history_does_not_invent_risk(
        self,
        mock_history,
        mock_freshness,
    ):
        mock_history.return_value = [
            legacy_observation()
        ]

        mock_freshness.return_value = {
            "status": "FRESH"
        }

        result = plant_history(
            "P01",
            10,
        )

        observation = result["observations"][0]

        self.assertIsNone(
            observation["risk"]
        )

        self.assertIsNone(
            observation["trend"]
        )

        self.assertFalse(
            observation[
                "field_availability"
            ][
                "risk_score"
            ]
        )


    def test_required_routes_preserved(self):

        routes = {
            route.path
            for route in app.routes
            if hasattr(route, "path")
        }

        required = {
            "/status",
            "/latest",
            "/events",
            "/plants/{plant_id}",
            "/model/info",
            "/inference",
            "/sensors",
        }

        self.assertTrue(
            required.issubset(routes)
        )


    def test_inference_uses_standard_contract(self):

        text = Path(
            "src/api.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "return build_standard_ai_output(",
            text,
        )

        self.assertIn(
            "latency_ms=latency_ms",
            text,
        )


    def test_audit_logging_precedes_standard_return(self):

        text = Path(
            "src/api.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        log_position = text.find(
            "log_observation(response, content)"
        )

        return_position = text.find(
            "return build_standard_ai_output("
        )

        self.assertGreaterEqual(
            log_position,
            0,
        )

        self.assertGreater(
            return_position,
            log_position,
        )


if __name__ == "__main__":
    unittest.main()
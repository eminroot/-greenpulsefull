
import copy
import unittest

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.real_multimodal_readiness import (
    assess_real_data_candidate
)


class RealDataContractTests(unittest.TestCase):

    def setUp(self):
        now = datetime.now(timezone.utc)

        self.record = {
            "sample_id": str(uuid4()),
            "plant_id": "TOM-001",
            "session_id": "SESSION-001",
            "crop": "tomato",
            "data_origin": "UNVERIFIED_CANDIDATE",
            "camera": {
                "camera_model": "ESP32-CAM+OV2640",
                "device_id": "CAM-001",
                "captured_at": now.isoformat(),
                "image_sha256": "a" * 64,
                "provenance": "UNVERIFIED_DEVICE_CLAIM"
            },
            "sensor": {
                "device_id": "SENSOR-001",
                "observed_at": (
                    now - timedelta(seconds=30)
                ).isoformat(),
                "soil_moisture_pct": 35.0,
                "air_temperature_c": 26.0,
                "relative_humidity_pct": 65.0,
                "calibration_record_id": None,
                "provenance": "UNVERIFIED_DEVICE_CLAIM"
            },
            "ground_truth": {
                "label": "UNLABELLED",
                "verification": "NONE"
            }
        }

    def test_01_candidate_is_not_training_ready(self):
        result = assess_real_data_candidate(
            self.record
        )

        self.assertTrue(
            result["schema_valid"]
        )

        self.assertTrue(
            result["image_sensor_aligned"]
        )

        self.assertFalse(
            result["training_eligible"]
        )

        self.assertFalse(
            result["operational_actuation_allowed"]
        )

    def test_02_simulated_origin_rejected(self):
        record = copy.deepcopy(self.record)

        record["data_origin"] = "SIMULATED"

        result = assess_real_data_candidate(
            record
        )

        self.assertFalse(
            result["schema_valid"]
        )

    def test_03_unsynchronized_data_flagged(self):
        record = copy.deepcopy(self.record)

        now = datetime.now(timezone.utc)

        record["sensor"]["observed_at"] = (
            now - timedelta(minutes=10)
        ).isoformat()

        result = assess_real_data_candidate(
            record
        )

        self.assertFalse(
            result["image_sensor_aligned"]
        )

        self.assertIn(
            "IMAGE_SENSOR_TIME_MISMATCH",
            result["blocking_reasons"]
        )

    def test_04_invalid_sensor_rejected(self):
        record = copy.deepcopy(self.record)

        record["sensor"][
            "soil_moisture_pct"
        ] = -10

        result = assess_real_data_candidate(
            record
        )

        self.assertFalse(
            result["schema_valid"]
        )

    def test_05_unverified_label_rejected(self):
        record = copy.deepcopy(self.record)

        record["ground_truth"][
            "label"
        ] = "WATER_STRESS"

        result = assess_real_data_candidate(
            record
        )

        self.assertFalse(
            result["schema_valid"]
        )

    def test_06_calibration_claim_not_enough(self):
        record = copy.deepcopy(self.record)

        record["sensor"][
            "calibration_record_id"
        ] = "CAL-001"

        result = assess_real_data_candidate(
            record
        )

        self.assertFalse(
            result["training_eligible"]
        )

        self.assertIn(
            "SENSOR_CALIBRATION_NOT_INDEPENDENTLY_VERIFIED",
            result["blocking_reasons"]
        )


if __name__ == "__main__":
    unittest.main()

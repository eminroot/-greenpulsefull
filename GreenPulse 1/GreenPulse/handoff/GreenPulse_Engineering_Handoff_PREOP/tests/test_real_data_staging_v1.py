
import copy
import hashlib
import tempfile
import unittest

from datetime import (
    datetime,
    timedelta,
    timezone
)

from pathlib import Path
from uuid import uuid4

from PIL import Image

from src.real_data_staging import (
    stage_multimodal_candidate
)


class RealDataStagingTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.staging = self.root / "staging"
        self.image = self.root / "test.jpg"

        # Synthetic image used only for testing.
        Image.new(
            "RGB",
            (128, 128),
            (35, 120, 45)
        ).save(
            self.image,
            format="JPEG"
        )

        digest = hashlib.sha256(
            self.image.read_bytes()
        ).hexdigest()

        now = datetime.now(timezone.utc)

        self.metadata = {
            "sample_id": str(uuid4()),
            "plant_id": "TOM-001",
            "session_id": "SESSION-001",
            "crop": "tomato",
            "data_origin": "UNVERIFIED_CANDIDATE",
            "camera": {
                "camera_model": "ESP32-CAM+OV2640",
                "device_id": "CAM-001",
                "captured_at": now.isoformat(),
                "image_sha256": digest,
                "provenance":
                    "UNVERIFIED_DEVICE_CLAIM"
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
                "provenance":
                    "UNVERIFIED_DEVICE_CLAIM"
            },
            "ground_truth": {
                "label": "UNLABELLED",
                "verification": "NONE"
            }
        }

    def test_01_valid_candidate_staged(self):
        result = stage_multimodal_candidate(
            self.image,
            self.metadata,
            self.staging
        )

        folder = Path(
            result["staging_path"]
        )

        self.assertTrue(
            (folder / "frame.jpg").is_file()
        )

        self.assertTrue(
            (folder / "metadata.json").is_file()
        )

        self.assertTrue(
            (folder / "intake_report.json").is_file()
        )

        self.assertFalse(
            result["training_eligible"]
        )

        self.assertFalse(
            result["physical_actuation_allowed"]
        )

    def test_02_hash_mismatch_rejected(self):
        record = copy.deepcopy(
            self.metadata
        )

        record["camera"][
            "image_sha256"
        ] = "0" * 64

        with self.assertRaises(ValueError):
            stage_multimodal_candidate(
                self.image,
                record,
                self.staging
            )

    def test_03_duplicate_sample_blocked(self):
        stage_multimodal_candidate(
            self.image,
            self.metadata,
            self.staging
        )

        with self.assertRaises(
            FileExistsError
        ):
            stage_multimodal_candidate(
                self.image,
                self.metadata,
                self.staging
            )

    def test_04_invalid_metadata_rejected(self):
        record = copy.deepcopy(
            self.metadata
        )

        record["data_origin"] = (
            "SIMULATED"
        )

        with self.assertRaises(ValueError):
            stage_multimodal_candidate(
                self.image,
                record,
                self.staging
            )

    def test_05_corrupt_image_rejected(self):
        bad_image = (
            self.root / "corrupt.jpg"
        )

        bad_image.write_bytes(
            b"not a valid image"
        )

        record = copy.deepcopy(
            self.metadata
        )

        record["sample_id"] = str(
            uuid4()
        )

        record["camera"][
            "image_sha256"
        ] = hashlib.sha256(
            bad_image.read_bytes()
        ).hexdigest()

        with self.assertRaises(ValueError):
            stage_multimodal_candidate(
                bad_image,
                record,
                self.staging
            )

    def test_06_unaligned_candidate_flagged(self):
        record = copy.deepcopy(
            self.metadata
        )

        record["sample_id"] = str(
            uuid4()
        )

        record["sensor"][
            "observed_at"
        ] = (
            datetime.now(timezone.utc)
            - timedelta(hours=1)
        ).isoformat()

        result = stage_multimodal_candidate(
            self.image,
            record,
            self.staging
        )

        self.assertFalse(
            result["readiness"][
                "image_sensor_aligned"
            ]
        )

        self.assertFalse(
            result["training_eligible"]
        )


if __name__ == "__main__":
    unittest.main()

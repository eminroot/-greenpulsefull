
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

from src.candidate_dataset_manifest import (
    generate_candidate_manifest
)


class CandidateManifestTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.staging = self.root / "staging"
        self.report = self.root / "reports/manifest.json"

        self.staging.mkdir()

    def stage(
        self,
        color,
        plant_id="TEST-TOM-001",
        sensor_age_seconds=30
    ):
        image = self.root / (
            str(uuid4()) + ".jpg"
        )

        Image.new(
            "RGB",
            (128, 128),
            color
        ).save(
            image,
            format="JPEG"
        )

        now = datetime.now(timezone.utc)

        metadata = {
            "sample_id": str(uuid4()),
            "plant_id": plant_id,
            "session_id": str(uuid4()),
            "crop": "tomato",
            "data_origin": "UNVERIFIED_CANDIDATE",
            "camera": {
                "camera_model": "ESP32-CAM+OV2640",
                "device_id": "TEST-CAMERA",
                "captured_at": now.isoformat(),
                "image_sha256": hashlib.sha256(
                    image.read_bytes()
                ).hexdigest(),
                "provenance":
                    "UNVERIFIED_DEVICE_CLAIM"
            },
            "sensor": {
                "device_id": "TEST-SENSOR",
                "observed_at": (
                    now - timedelta(
                        seconds=sensor_age_seconds
                    )
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

        stage_multimodal_candidate(
            image,
            metadata,
            self.staging
        )

    def generate(self):
        return generate_candidate_manifest(
            self.staging,
            self.report
        )

    def test_01_valid_candidate_inventory(self):
        self.stage((35, 120, 45))

        result = self.generate()

        self.assertEqual(
            result["total_samples"], 1
        )

        self.assertEqual(
            result["integrity_pass_count"], 1
        )

        self.assertTrue(
            self.report.is_file()
        )

        self.assertFalse(
            result["training_approved"]
        )

    def test_02_group_same_claimed_plant(self):
        self.stage((35, 120, 45))
        self.stage((75, 105, 55))

        result = self.generate()

        self.assertEqual(
            result["integrity_pass_count"], 2
        )

        groups = {
            item["plant_group_claim"]
            for item in result["samples"]
        }

        self.assertEqual(
            groups, {"TEST-TOM-001"}
        )

        self.assertFalse(
            result["verified_physical_plant_groups"]
        )

    def test_03_duplicate_images_flagged(self):
        self.stage((35, 120, 45))
        self.stage((35, 120, 45))

        result = self.generate()

        self.assertEqual(
            result["review_required_count"], 2
        )

        for sample in result["samples"]:
            self.assertIn(
                "DUPLICATE_IMAGE_CONTENT",
                sample["issues"]
            )

            self.assertFalse(
                sample["training_eligible"]
            )

    def test_04_unsynchronized_pair_flagged(self):
        self.stage(
            (35, 120, 45),
            sensor_age_seconds=3600
        )

        result = self.generate()

        self.assertEqual(
            result["review_required_count"], 1
        )

        self.assertFalse(
            result["samples"][0][
                "image_sensor_aligned"
            ]
        )

    def test_05_report_outside_staging(self):
        self.stage((35, 120, 45))

        with self.assertRaises(ValueError):
            generate_candidate_manifest(
                self.staging,
                self.staging / "manifest.json"
            )


if __name__ == "__main__":
    unittest.main()

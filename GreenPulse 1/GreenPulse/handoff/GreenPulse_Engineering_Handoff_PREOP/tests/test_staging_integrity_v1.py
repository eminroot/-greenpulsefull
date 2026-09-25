
import copy
import hashlib
import tempfile
import unittest

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from PIL import Image

from src.real_data_staging import (
    stage_multimodal_candidate
)

from src.staging_integrity_audit import (
    audit_staged_candidates
)


class StagingIntegrityTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.staging = self.root / "staging"
        self.staging.mkdir()

        self.image = self.root / "synthetic.jpg"

        Image.new(
            "RGB",
            (128, 128),
            (40, 115, 60)
        ).save(self.image, format="JPEG")

        now = datetime.now(timezone.utc)

        self.metadata = {
            "sample_id": str(uuid4()),
            "plant_id": "TEST-TOM-001",
            "session_id": "TEST-SESSION-001",
            "crop": "tomato",
            "data_origin": "UNVERIFIED_CANDIDATE",
            "camera": {
                "camera_model": "ESP32-CAM+OV2640",
                "device_id": "TEST-CAM",
                "captured_at": now.isoformat(),
                "image_sha256": hashlib.sha256(
                    self.image.read_bytes()
                ).hexdigest(),
                "provenance":
                    "UNVERIFIED_DEVICE_CLAIM"
            },
            "sensor": {
                "device_id": "TEST-SENSOR",
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

    def stage(self, metadata=None):
        return stage_multimodal_candidate(
            self.image,
            metadata or self.metadata,
            self.staging
        )

    def test_01_valid_file_integrity(self):
        self.stage()

        audit = audit_staged_candidates(
            self.staging
        )

        self.assertEqual(
            audit["integrity_pass_count"],
            1
        )

        self.assertFalse(
            audit["training_approved"]
        )

        self.assertFalse(
            audit["device_authentication_performed"]
        )

    def test_02_duplicate_image_detected(self):
        self.stage()

        duplicate = copy.deepcopy(
            self.metadata
        )

        duplicate["sample_id"] = str(
            uuid4()
        )

        self.stage(duplicate)

        audit = audit_staged_candidates(
            self.staging
        )

        self.assertEqual(
            audit["review_required_count"],
            2
        )

        for record in audit["samples"]:
            self.assertIn(
                "DUPLICATE_IMAGE_CONTENT",
                record["issues"]
            )

    def test_03_image_tampering_detected(self):
        result = self.stage()

        stored_image = (
            Path(result["staging_path"])
            / "frame.jpg"
        )

        stored_image.write_bytes(
            stored_image.read_bytes()
            + b"UNAUTHORIZED_CHANGE"
        )

        audit = audit_staged_candidates(
            self.staging
        )

        self.assertEqual(
            audit["review_required_count"],
            1
        )

        self.assertIn(
            "IMAGE_METADATA_HASH_MISMATCH",
            audit["samples"][0]["issues"]
        )

    def test_04_missing_report_detected(self):
        result = self.stage()

        report = (
            Path(result["staging_path"])
            / "intake_report.json"
        )

        report.unlink()

        audit = audit_staged_candidates(
            self.staging
        )

        self.assertEqual(
            audit["review_required_count"],
            1
        )

        self.assertIn(
            "METADATA_OR_REPORT_UNAVAILABLE",
            audit["samples"][0]["issues"]
        )

    def test_05_unsynchronized_pair_flagged(self):
        record = copy.deepcopy(
            self.metadata
        )

        record["sensor"]["observed_at"] = (
            datetime.now(timezone.utc)
            - timedelta(hours=1)
        ).isoformat()

        self.stage(record)

        audit = audit_staged_candidates(
            self.staging
        )

        self.assertFalse(
            audit["samples"][0][
                "image_sensor_aligned"
            ]
        )

        self.assertIn(
            "IMAGE_SENSOR_TIME_MISMATCH",
            audit["samples"][0]["issues"]
        )


if __name__ == "__main__":
    unittest.main()

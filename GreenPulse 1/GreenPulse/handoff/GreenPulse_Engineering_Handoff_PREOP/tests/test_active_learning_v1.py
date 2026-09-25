
import copy
import json
import tempfile
import unittest

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.active_learning import (
    assess_for_review,
    route_review_candidate
)

from src.review_queue import (
    list_pending_reviews
)


class ActiveLearningTests(unittest.TestCase):

    def setUp(self):

        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp.cleanup
        )

        self.root = Path(
            self.temp.name
        )

        self.db = (
            self.root / "review.db"
        )

        self.policy = (
            self.root / "policy.json"
        )

        self.policy_data = {
            "version": "1.0",
            "mode": "RESEARCH_ONLY",
            "low_confidence_threshold":
                0.65,
            "threshold_validated": False,
            "allowed_triggers": [
                "LOW_CONFIDENCE",
                "VISION_SENSOR_CONFLICT",
                "IMAGE_QUALITY_FAILURE",
                "MODEL_FAILURE",
                "OOD_SUSPECTED"
            ],
            "forbidden_source_partitions": [
                "TEST",
                "FINAL_TEST",
                "HELD_OUT_TEST",
                "FROZEN_FINAL_TEST"
            ],
            "automatic_retraining_allowed":
                False,
            "automatic_labeling_allowed":
                False,
            "physical_actuation_allowed":
                False
        }

        self.save_policy()

        self.event = {
            "sample_id": str(uuid4()),
            "crop": "bell_pepper",
            "source_partition":
                "LIVE_UNLABELLED",
            "observed_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
            "model_sha256":
                "a" * 64,
            "confidence": 0.95,
            "vision_sensor_conflict":
                False,
            "image_quality_pass":
                True,
            "inference_error":
                False,
            "ood_suspected":
                False
        }

    def save_policy(self):
        self.policy.write_text(
            json.dumps(
                self.policy_data
            ),
            encoding="utf-8"
        )

    def test_01_low_confidence_queued(self):

        event = copy.deepcopy(
            self.event
        )

        event["confidence"] = 0.40

        result = route_review_candidate(
            event,
            self.db,
            self.policy
        )

        self.assertEqual(
            result["status"],
            "PENDING_HUMAN_REVIEW"
        )

        self.assertTrue(
            result["queued"]
        )

        self.assertFalse(
            result[
                "automatic_retraining_allowed"
            ]
        )

        self.assertEqual(
            len(
                list_pending_reviews(
                    self.db
                )
            ),
            1
        )

    def test_02_high_confidence_clean_not_queued(self):

        result = route_review_candidate(
            self.event,
            self.db,
            self.policy
        )

        self.assertEqual(
            result["status"],
            "NO_REVIEW_REQUIRED"
        )

        self.assertEqual(
            len(
                list_pending_reviews(
                    self.db
                )
            ),
            0
        )

    def test_03_conflict_is_reviewed(self):

        event = copy.deepcopy(
            self.event
        )

        event[
            "vision_sensor_conflict"
        ] = True

        result = route_review_candidate(
            event,
            self.db,
            self.policy
        )

        self.assertIn(
            "VISION_SENSOR_CONFLICT",
            result["assessment"][
                "review_triggers"
            ]
        )

    def test_04_final_test_forbidden(self):

        event = copy.deepcopy(
            self.event
        )

        event[
            "source_partition"
        ] = "FROZEN_FINAL_TEST"

        with self.assertRaisesRegex(
            ValueError,
            "FINAL_TEST_DATA_FORBIDDEN"
        ):
            assess_for_review(
                event,
                self.policy
            )

    def test_05_duplicate_queue_is_idempotent(self):

        event = copy.deepcopy(
            self.event
        )

        event["ood_suspected"] = True

        first = route_review_candidate(
            event,
            self.db,
            self.policy
        )

        second = route_review_candidate(
            event,
            self.db,
            self.policy
        )

        self.assertTrue(
            first["queued"]
        )

        self.assertFalse(
            second["queued"]
        )

        self.assertEqual(
            len(
                list_pending_reviews(
                    self.db
                )
            ),
            1
        )

    def test_06_unsafe_retraining_policy_rejected(self):

        self.policy_data[
            "automatic_retraining_allowed"
        ] = True

        self.save_policy()

        with self.assertRaisesRegex(
            ValueError,
            "AUTOMATIC_RETRAINING_FORBIDDEN"
        ):
            assess_for_review(
                self.event,
                self.policy
            )

    def test_07_quality_failure_is_reviewed(self):

        event = copy.deepcopy(
            self.event
        )

        event[
            "image_quality_pass"
        ] = False

        result = route_review_candidate(
            event,
            self.db,
            self.policy
        )

        self.assertIn(
            "IMAGE_QUALITY_FAILURE",
            result["assessment"][
                "review_triggers"
            ]
        )

        self.assertFalse(
            result[
                "physical_actuation_allowed"
            ]
        )


if __name__ == "__main__":
    unittest.main()

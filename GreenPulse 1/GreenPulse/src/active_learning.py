
import hashlib
import json
import math

from datetime import datetime
from pathlib import Path
from uuid import UUID

from src.review_queue import (
    enqueue_review
)


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_POLICY = (
    ROOT / "configs/active_learning_policy_v1.json"
)


def load_policy(path=DEFAULT_POLICY):

    policy = json.loads(
        Path(path).read_text(
            encoding="utf-8-sig"
        )
    )

    if policy.get("version") != "1.0":
        raise ValueError(
            "ACTIVE_LEARNING_POLICY_VERSION_INVALID"
        )

    if policy.get("mode") != "RESEARCH_ONLY":
        raise ValueError(
            "ACTIVE_LEARNING_MODE_UNSAFE"
        )

    threshold = policy.get(
        "low_confidence_threshold"
    )

    if (
        not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or not math.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError(
            "INVALID_CONFIDENCE_THRESHOLD"
        )

    if policy.get(
        "threshold_validated"
    ) is not False:
        raise ValueError(
            "UNSUPPORTED_THRESHOLD_VALIDATION_CLAIM"
        )

    if policy.get(
        "automatic_retraining_allowed"
    ) is not False:
        raise ValueError(
            "AUTOMATIC_RETRAINING_FORBIDDEN"
        )

    if policy.get(
        "automatic_labeling_allowed"
    ) is not False:
        raise ValueError(
            "AUTOMATIC_LABELING_FORBIDDEN"
        )

    if policy.get(
        "physical_actuation_allowed"
    ) is not False:
        raise ValueError(
            "PHYSICAL_ACTUATION_FORBIDDEN"
        )

    return policy


def parse_time(value):

    if not isinstance(value, str):
        raise ValueError(
            "INVALID_OBSERVED_AT"
        )

    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        raise ValueError(
            "OBSERVED_AT_REQUIRES_TIMEZONE"
        )

    return parsed


def validate_sha256(value):

    if (
        not isinstance(value, str)
        or len(value) != 64
    ):
        raise ValueError(
            "INVALID_MODEL_SHA256"
        )

    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(
            "INVALID_MODEL_SHA256"
        ) from exc

    return value.lower()


def assess_for_review(
    event,
    policy_path=DEFAULT_POLICY
):

    if not isinstance(event, dict):
        raise ValueError(
            "EVENT_MUST_BE_OBJECT"
        )

    policy = load_policy(
        policy_path
    )

    required = {
        "sample_id",
        "crop",
        "source_partition",
        "observed_at",
        "model_sha256",
        "confidence",
        "vision_sensor_conflict",
        "image_quality_pass",
        "inference_error",
        "ood_suspected"
    }

    if set(event) != required:
        raise ValueError(
            "ACTIVE_LEARNING_EVENT_FIELDS_INVALID"
        )

    sample_id = str(
        UUID(event["sample_id"])
    )

    crop = event["crop"]

    if (
        not isinstance(crop, str)
        or not crop.strip()
    ):
        raise ValueError(
            "INVALID_CROP"
        )

    source_partition = (
        event["source_partition"]
    )

    if (
        not isinstance(source_partition, str)
        or not source_partition
    ):
        raise ValueError(
            "INVALID_SOURCE_PARTITION"
        )

    if (
        source_partition
        in policy[
            "forbidden_source_partitions"
        ]
    ):
        raise ValueError(
            "FINAL_TEST_DATA_FORBIDDEN"
        )

    parse_time(
        event["observed_at"]
    )

    model_sha256 = validate_sha256(
        event["model_sha256"]
    )

    confidence = event[
        "confidence"
    ]

    if confidence is not None:

        if (
            isinstance(confidence, bool)
            or not isinstance(
                confidence,
                (int, float)
            )
            or not math.isfinite(
                confidence
            )
            or not 0 <= confidence <= 1
        ):
            raise ValueError(
                "INVALID_CONFIDENCE"
            )

    for field in (
        "vision_sensor_conflict",
        "image_quality_pass",
        "inference_error",
        "ood_suspected"
    ):
        if not isinstance(
            event[field],
            bool
        ):
            raise ValueError(
                "BOOLEAN_FIELD_INVALID"
            )

    triggers = []

    if (
        confidence is not None
        and confidence
        <= policy[
            "low_confidence_threshold"
        ]
    ):
        triggers.append(
            "LOW_CONFIDENCE"
        )

    if event[
        "vision_sensor_conflict"
    ]:
        triggers.append(
            "VISION_SENSOR_CONFLICT"
        )

    if not event[
        "image_quality_pass"
    ]:
        triggers.append(
            "IMAGE_QUALITY_FAILURE"
        )

    if event[
        "inference_error"
    ]:
        triggers.append(
            "MODEL_FAILURE"
        )

    if event[
        "ood_suspected"
    ]:
        triggers.append(
            "OOD_SUSPECTED"
        )

    unsupported = (
        set(triggers)
        - set(
            policy[
                "allowed_triggers"
            ]
        )
    )

    if unsupported:
        raise ValueError(
            "UNSUPPORTED_REVIEW_TRIGGER"
        )

    review_required = (
        len(triggers) > 0
    )

    normalized = {
        "sample_id": sample_id,
        "crop": crop.strip(),
        "source_partition":
            source_partition,
        "observed_at":
            event["observed_at"],
        "model_sha256":
            model_sha256,
        "confidence":
            confidence,
        "review_triggers":
            triggers,
        "review_required":
            review_required,
        "human_review_required":
            review_required,
        "training_eligible":
            False,
        "automatic_labeling_allowed":
            False,
        "automatic_retraining_allowed":
            False,
        "physical_actuation_allowed":
            False
    }

    return normalized


def route_review_candidate(
    event,
    db_path,
    policy_path=DEFAULT_POLICY
):

    assessment = assess_for_review(
        event,
        policy_path
    )

    if not assessment[
        "review_required"
    ]:

        return {
            "status":
                "NO_REVIEW_REQUIRED",
            "queued": False,
            "assessment":
                assessment,
            "automatic_retraining_allowed":
                False,
            "physical_actuation_allowed":
                False
        }

    key_material = (
        assessment["sample_id"]
        + "|"
        + assessment["model_sha256"]
    ).encode("utf-8")

    queue_key = hashlib.sha256(
        key_material
    ).hexdigest()

    result = enqueue_review(
        queue_key,
        assessment,
        db_path=db_path
    )

    return {
        "status":
            "PENDING_HUMAN_REVIEW",
        "queued":
            result["inserted"],
        "queue_key":
            queue_key,
        "assessment":
            assessment,
        "automatic_retraining_allowed":
            False,
        "physical_actuation_allowed":
            False
    }

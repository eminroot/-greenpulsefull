
from datetime import datetime, timezone


def check_observation_freshness(
    timestamp,
    max_age_seconds=300
):
    """
    Checks when an AI observation was recorded.
    This does NOT verify image or sensor freshness.
    """

    try:
        recorded = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

        if recorded.tzinfo is None:
            raise ValueError("Timezone required.")

        now = datetime.now(timezone.utc)
        age = (now - recorded).total_seconds()

    except (ValueError, TypeError, AttributeError):
        return {
            "status": "INVALID_TIMESTAMP",
            "age_seconds": None
        }

    if age < -30:
        status = "FUTURE_TIMESTAMP"
    elif age < 0:
        status = "CLOCK_SKEW"
    elif age > max_age_seconds:
        status = "STALE_RECORD"
    else:
        status = "RECENT_RECORD"

    return {
        "status": status,
        "age_seconds": round(age, 2)
    }

from datetime import datetime, timezone
import math


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")

    dt = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if dt.tzinfo is None:
        raise ValueError("Timezone is required")

    return dt.astimezone(timezone.utc)


def synchronize(
    image_captured_at,
    sensor_timestamp,
    max_delta_seconds=60,
    max_age_seconds=300
):
    if not image_captured_at:
        return {
            "status": "UNKNOWN_CAPTURE_TIME",
            "delta_seconds": None
        }

    try:
        image_time = parse_timestamp(image_captured_at)
        sensor_time = parse_timestamp(sensor_timestamp)
    except (ValueError, TypeError, AttributeError):
        return {
            "status": "INVALID_TIMESTAMP",
            "delta_seconds": None
        }

    now = datetime.now(timezone.utc)

    image_age = (now - image_time).total_seconds()
    sensor_age = (now - sensor_time).total_seconds()

    if min(image_age, sensor_age) < -30:
        status = "FUTURE_TIMESTAMP"

    elif max(image_age, sensor_age) > max_age_seconds:
        status = "STALE"

    else:
        delta = abs(
            (image_time - sensor_time).total_seconds()
        )

        status = (
            "SYNCED"
            if delta <= max_delta_seconds
            else "OUT_OF_SYNC"
        )

    return {
        "status": status,
        "delta_seconds": round(
            abs((image_time - sensor_time).total_seconds()),
            3
        )
    }


if __name__ == "__main__":
    from datetime import timedelta

    now = datetime.now(timezone.utc)

    image_time = now.isoformat()

    sensor_time = (
        now - timedelta(seconds=25)
    ).isoformat()

    result = synchronize(
        image_time,
        sensor_time
    )

    print("\nGREENPULSE TIME SYNCHRONIZATION")
    print("--------------------------------")
    print("STATUS:", result["status"])
    print("TIME DIFFERENCE:", result["delta_seconds"], "seconds")

    assert result["status"] == "SYNCED"

    outdated_pair = synchronize(
        image_time,
        (now - timedelta(seconds=240)).isoformat()
    )

    assert outdated_pair["status"] == "OUT_OF_SYNC"

    unknown = synchronize(None, sensor_time)

    assert unknown["status"] == "UNKNOWN_CAPTURE_TIME"

    print("Synchronization checks: PASS")

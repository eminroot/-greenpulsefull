
from datetime import datetime, timezone

from src.sensor_contract_guard import check_sensor_contract
from src.sensor_validator import validate_sensor


def parse_time(value):
    dt = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if dt.tzinfo is None:
        raise ValueError("Timezone required.")

    return dt.astimezone(timezone.utc)


def calculate_sensor_window(
    current,
    observations,
    window_minutes=30
):
    """Calculate sample averages from eligible sensor readings."""

    valid, errors = check_sensor_contract(current)

    if not valid:
        raise ValueError("; ".join(errors))

    status, reason = validate_sensor(current)

    if status not in ("VALID", "VALID_SIMULATED"):
        raise ValueError(f"Current sensor rejected: {reason}")

    if not 1 <= window_minutes <= 60:
        raise ValueError("Window must be 1?60 minutes.")

    current_time = parse_time(current["timestamp"])
    samples = {current_time: current}

    for observation in observations:

        if observation.get("plant_id") != current["plant_id"]:
            continue

        sensor = observation.get("sensor") or {}
        previous = sensor.get("data")

        if not isinstance(previous, dict):
            continue

        if sensor.get("status") != status:
            continue

        valid, _ = check_sensor_contract(previous)

        if not valid:
            continue

        if (
            previous["plant_id"] != current["plant_id"]
            or previous["source"] != current["source"]
            or previous["soil_calibrated"]
            != current["soil_calibrated"]
        ):
            continue

        try:
            previous_time = parse_time(
                previous["timestamp"]
            )
        except (ValueError, TypeError, AttributeError):
            continue

        age = (
            current_time - previous_time
        ).total_seconds()

        if not 0 < age <= window_minutes * 60:
            continue

        if previous_time in samples:
            existing = samples[previous_time]

            if existing != previous:
                return {
                    "status": "HISTORY_TIMESTAMP_CONFLICT",
                    "sample_count": None,
                    "averages": None
                }

            continue

        samples[previous_time] = previous

    if len(samples) < 3:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "sample_count": len(samples),
            "averages": None
        }

    values = list(samples.values())

    def average(field):
        return round(
            sum(float(p[field]) for p in values)
            / len(values),
            3
        )

    return {
        "status": (
            "SIMULATED_WINDOW"
            if current["source"] == "SIMULATED"
            else "DEVICE_UNVERIFIED_WINDOW"
        ),
        "window_minutes": window_minutes,
        "sample_count": len(values),
        "average_type": "SAMPLE_MEAN",
        "averages": {
            "soil_moisture_pct": average(
                "soil_moisture_pct"
            ),
            "temperature_c": average(
                "temperature_c"
            ),
            "humidity_pct": average(
                "humidity_pct"
            )
        }
    }


from datetime import datetime, timezone

from src.sensor_contract_guard import check_sensor_contract


def parse_time(value):
    result = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if result.tzinfo is None:
        raise ValueError("Timezone required.")

    return result.astimezone(timezone.utc)


def select_previous_sensor(current, observations):
    """
    Select the nearest eligible previous sensor packet.

    Never mix different plants or simulated/real sources.
    """

    valid, errors = check_sensor_contract(current)

    if not valid:
        raise ValueError(
            "Invalid current packet: " + "; ".join(errors)
        )

    current_time = parse_time(current["timestamp"])

    best_packet = None
    best_interval = None

    for observation in observations:

        if observation.get("plant_id") != current["plant_id"]:
            continue

        sensor = observation.get("sensor") or {}
        previous = sensor.get("data")

        if not isinstance(previous, dict):
            continue

        expected_status = (
            "VALID_SIMULATED"
            if current["source"] == "SIMULATED"
            else "VALID"
        )

        if sensor.get("status") != expected_status:
            continue

        valid, _ = check_sensor_contract(previous)

        if not valid:
            continue

        if previous["plant_id"] != current["plant_id"]:
            continue

        if previous["source"] != current["source"]:
            continue

        if previous["soil_calibrated"] != current["soil_calibrated"]:
            continue

        try:
            interval = (
                current_time - parse_time(previous["timestamp"])
            ).total_seconds()
        except (ValueError, TypeError, AttributeError):
            continue

        # Compare only measurements 1?60 minutes apart.
        if not 60 <= interval <= 3600:
            continue

        if (
            best_interval is None
            or interval < best_interval
        ):
            best_packet = previous
            best_interval = interval

    return best_packet

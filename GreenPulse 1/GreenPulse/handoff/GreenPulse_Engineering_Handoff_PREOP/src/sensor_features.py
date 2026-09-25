
from datetime import datetime, timezone

from src.sensor_contract_guard import check_sensor_contract
from src.sensor_validator import validate_sensor


FEATURE_VERSION = "1.0"


def parse_time(value):
    dt = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )
    return dt.astimezone(timezone.utc)


def extract_sensor_features(packet, previous=None):

    valid, errors = check_sensor_contract(packet)

    if not valid:
        raise ValueError(
            "Invalid sensor packet: " + "; ".join(errors)
        )

    status, reason = validate_sensor(packet)

    if status not in ("VALID", "VALID_SIMULATED"):
        raise ValueError(
            f"Sensor rejected: {status}, {reason}"
        )

    simulated = packet["source"] == "SIMULATED"

    result = {
        "feature_version": FEATURE_VERSION,
        "plant_id": packet["plant_id"],
        "timestamp": packet["timestamp"],

        "provenance": {
            "source": packet["source"],
            "device_authenticated": False,
            "soil_calibration_claimed": packet[
                "soil_calibrated"
            ]
        },

        "status": (
            "SIMULATED_ONLY"
            if simulated
            else "DEVICE_UNVERIFIED"
        ),

        "current": {
            "soil_moisture_pct": float(
                packet["soil_moisture_pct"]
            ),
            "temperature_c": float(
                packet["temperature_c"]
            ),
            "humidity_pct": float(
                packet["humidity_pct"]
            )
        },

        "trend": {
            "status": "INSUFFICIENT_HISTORY",
            "interval_seconds": None,
            "soil_moisture_delta": None,
            "soil_moisture_change_per_hour": None,
            "temperature_delta_c": None,
            "humidity_delta_pct": None
        }
    }

    if previous is None:
        return result

    previous_valid, _ = check_sensor_contract(previous)

    if not previous_valid:
        return result

    if previous["plant_id"] != packet["plant_id"]:
        return result

    if previous["source"] != packet["source"]:
        return result

    interval = (
        parse_time(packet["timestamp"])
        - parse_time(previous["timestamp"])
    ).total_seconds()

    # Reject reversed, excessively close or distant samples.
    if not 60 <= interval <= 3600:
        return result

    soil_delta = (
        packet["soil_moisture_pct"]
        - previous["soil_moisture_pct"]
    )

    result["trend"] = {
        "status": (
            "SIMULATED_TREND"
            if simulated
            else "UNVERIFIED_DEVICE_TREND"
        ),
        "interval_seconds": round(interval, 2),
        "soil_moisture_delta": round(soil_delta, 3),
        "soil_moisture_change_per_hour": round(
            soil_delta * 3600 / interval, 3
        ),
        "temperature_delta_c": round(
            packet["temperature_c"]
            - previous["temperature_c"], 3
        ),
        "humidity_delta_pct": round(
            packet["humidity_pct"]
            - previous["humidity_pct"], 3
        )
    }

    return result

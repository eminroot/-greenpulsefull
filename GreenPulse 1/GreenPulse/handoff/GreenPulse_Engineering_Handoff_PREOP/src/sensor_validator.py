from datetime import datetime, timezone, timedelta
import json
import math

REQUIRED = [
    "plant_id",
    "timestamp",
    "soil_moisture_pct",
    "temperature_c",
    "humidity_pct",
    "soil_calibrated",
    "source"
]

def validate_sensor(data):

    for field in REQUIRED:
        if field not in data:
            return "MISSING", field

    if not isinstance(data["plant_id"], str) or not data["plant_id"].strip():
        return "INVALID", "plant_id"

    if data["source"] not in ["SIMULATED", "REAL"]:
        return "INVALID", "source"

    for field in [
        "soil_moisture_pct",
        "temperature_c",
        "humidity_pct"
    ]:
        value = data[field]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "INVALID", field

        if not math.isfinite(value):
            return "INVALID", field

    if not 0 <= data["soil_moisture_pct"] <= 100:
        return "INVALID", "soil_moisture_pct"

    if not -10 <= data["temperature_c"] <= 65:
        return "INVALID", "temperature_c"

    if not 0 <= data["humidity_pct"] <= 100:
        return "INVALID", "humidity_pct"

    if type(data["soil_calibrated"]) is not bool:
        return "INVALID", "soil_calibrated"

    try:
        timestamp = datetime.fromisoformat(
            data["timestamp"].replace("Z", "+00:00")
        )

        if timestamp.tzinfo is None:
            return "INVALID", "timestamp_timezone"

        now = datetime.now(timezone.utc)
        age = (now - timestamp).total_seconds()

        if age < -30:
            return "INVALID", "future_timestamp"

        if age > 300:
            return "STALE", "timestamp"

    except (ValueError, TypeError, AttributeError):
        return "INVALID", "timestamp"

    if not data["soil_calibrated"]:
        return "INVALID", "soil_not_calibrated"

    if data["source"] == "SIMULATED":
        return "VALID_SIMULATED", "simulation_only"

    return "VALID", "all_checks_passed"


if __name__ == "__main__":

    sample = {
        "plant_id": "TOM-P01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "soil_moisture_pct": 45.0,
        "temperature_c": 26.5,
        "humidity_pct": 65.0,
        "soil_calibrated": True,
        "source": "SIMULATED"
    }

    cases = {
        "NORMAL": sample,
        "MISSING": {
            k: v for k, v in sample.items()
            if k != "temperature_c"
        },
        "INVALID": {
            **sample,
            "humidity_pct": 150
        },
        "STALE": {
            **sample,
            "timestamp": (
                datetime.now(timezone.utc)
                - timedelta(minutes=10)
            ).isoformat()
        }
    }

    expected = {
        "NORMAL": "VALID_SIMULATED",
        "MISSING": "MISSING",
        "INVALID": "INVALID",
        "STALE": "STALE"
    }

    print("\nGREENPULSE SENSOR VALIDATION")
    print("------------------------------")

    for name, packet in cases.items():
        status, reason = validate_sensor(packet)

        assert status == expected[name], (
            f"{name}: expected {expected[name]}, got {status}"
        )

        print(f"{name}: {status} ({reason})")

    print("------------------------------")
    print("ALL SENSOR VALIDATION TESTS PASSED")

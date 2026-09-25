import json
import sys
from pathlib import Path
from datetime import datetime, timezone

CONFIG = Path("configs")
FIXTURES = Path("tests/fixtures")

CONFIG.mkdir(parents=True, exist_ok=True)
FIXTURES.mkdir(parents=True, exist_ok=True)

schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "GreenPulse Sensor Packet",
    "description": "AI-Hardware sensor interface v1.0",
    "type": "object",
    "required": [
        "plant_id",
        "timestamp",
        "soil_moisture_pct",
        "temperature_c",
        "humidity_pct",
        "soil_calibrated",
        "source"
    ],
    "properties": {
        "plant_id": {
            "type": "string",
            "minLength": 1
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "Timezone-aware ISO 8601 timestamp"
        },
        "soil_moisture_pct": {
            "type": "number",
            "minimum": 0,
            "maximum": 100
        },
        "temperature_c": {
            "type": "number",
            "minimum": -10,
            "maximum": 65
        },
        "humidity_pct": {
            "type": "number",
            "minimum": 0,
            "maximum": 100
        },
        "soil_calibrated": {
            "type": "boolean"
        },
        "source": {
            "type": "string",
            "enum": ["REAL", "SIMULATED"]
        }
    },
    "additionalProperties": False
}

sample = {
    "plant_id": "TOM-P01",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "soil_moisture_pct": 45.0,
    "temperature_c": 26.5,
    "humidity_pct": 65.0,
    "soil_calibrated": True,
    "source": "SIMULATED"
}

schema_path = CONFIG / "sensor_schema_v1.json"
sample_path = FIXTURES / "sensor_valid_simulated.json"

schema_path.write_text(
    json.dumps(schema, indent=4),
    encoding="utf-8"
)

sample_path.write_text(
    json.dumps(sample, indent=4),
    encoding="utf-8"
)

sys.path.insert(0, str(Path("src").resolve()))

from sensor_validator import validate_sensor

status, reason = validate_sensor(sample)

assert status == "VALID_SIMULATED"

assert set(schema["required"]) == set(sample)
assert all(field in schema["properties"] for field in sample)

print("\nGREENPULSE SENSOR CONTRACT")
print("--------------------------------")
print("SCHEMA:", schema_path)
print("EXAMPLE:", sample_path)
print("SENSOR STATUS:", status)
print("REASON:", reason)
print("SCHEMA STRUCTURE: OK")
print("--------------------------------")
print("INITIAL SENSOR CONTRACT CREATED!")

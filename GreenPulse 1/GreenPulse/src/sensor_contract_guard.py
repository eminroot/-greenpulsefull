
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "sensor_schema_v1.json"
)

with SCHEMA_PATH.open("r", encoding="utf-8-sig") as file:
    SCHEMA = json.load(file)

Draft202012Validator.check_schema(SCHEMA)

VALIDATOR = Draft202012Validator(
    SCHEMA,
    format_checker=FormatChecker()
)


def check_sensor_contract(packet):
    """Check sensor data against the project JSON schema."""

    if not isinstance(packet, dict):
        return False, ["Sensor packet must be a JSON object."]

    errors = sorted(
        VALIDATOR.iter_errors(packet),
        key=lambda error: str(error.path)
    )

    if errors:
        return False, [error.message for error in errors]

    return True, []

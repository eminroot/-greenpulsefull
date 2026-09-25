
import json
from pathlib import Path
from datetime import datetime, timezone
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker


SIMULATOR_VERSION = "0.2.0"

_ROOT = Path(__file__).resolve().parents[1]

_COMMAND_SCHEMA = json.loads(
    (_ROOT / "configs/actuator_schema_v1.json").read_text(
        encoding="utf-8-sig"
    )
)

_ACK_SCHEMA = json.loads(
    (_ROOT / "configs/ack_error_schema_v1.json").read_text(
        encoding="utf-8-sig"
    )
)

Draft202012Validator.check_schema(_COMMAND_SCHEMA)
Draft202012Validator.check_schema(_ACK_SCHEMA)

_COMMAND_VALIDATOR = Draft202012Validator(
    _COMMAND_SCHEMA,
    format_checker=FormatChecker()
)

_ACK_VALIDATOR = Draft202012Validator(
    _ACK_SCHEMA,
    format_checker=FormatChecker()
)


def simulate_actuator(command, scenario="SUCCESS"):
    """
    Software-only actuator simulator.

    Never connects to GPIO, pumps, relays,
    networks or physical hardware.
    """

    if not isinstance(command, dict):
        raise ValueError("Command must be a dictionary.")

    def valid_uuid(value):
        try:
            UUID(str(value))
            return True
        except (ValueError, TypeError, AttributeError):
            return False

    required = (
        valid_uuid(command.get("command_id"))
        and valid_uuid(command.get("observation_id"))
        and isinstance(command.get("plant_id"), str)
        and 1 <= len(command.get("plant_id", "")) <= 64
        and command.get("mode") == "SIMULATION_ONLY"
        and command.get("test_only") is True
        and command.get("origin") == "TEST_HARNESS"
        and command.get("action") == "IRRIGATION_TEST"
        and _COMMAND_VALIDATOR.is_valid(command)
    )

    target = command.get("target")

    if target == "MAIN_IRRIGATION_PUMP":
        target_allowed = True
    else:
        target_allowed = False

    if not required or not target_allowed:
        status = "SIMULATED_REJECTED"
        error = "COMMAND_NOT_AUTHORIZED"

    elif scenario == "SUCCESS":
        status = "SIMULATED_EXECUTED"
        error = None

    elif scenario == "FAILURE":
        status = "SIMULATED_FAILED"
        error = "SIMULATED_PUMP_FAILURE"

    elif scenario == "TIMEOUT":
        status = "SIMULATED_TIMEOUT"
        error = "SIMULATED_CONTROLLER_TIMEOUT"

    else:
        status = "SIMULATED_REJECTED"
        error = "UNKNOWN_TEST_SCENARIO"

    result = {
        "simulator_version": SIMULATOR_VERSION,
        "command_id": (
            str(UUID(str(command["command_id"])))
            if valid_uuid(command.get("command_id"))
            else None
        ),
        "observation_id": (
            str(UUID(str(command["observation_id"])))
            if valid_uuid(command.get("observation_id"))
            else None
        ),
        "plant_id": (
            command.get("plant_id")
            if isinstance(command.get("plant_id"), str)
            else None
        ),
        "target": (
            target
            if isinstance(target, str)
            else None
        ),
        "status": status,
        "error_code": error,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "simulated": True,
        "physical_actuation": False,
        "real_hardware_ack": None
    }

    # Every simulator response must satisfy
    # the official ACK/error contract.
    _ACK_VALIDATOR.validate(result)

    return result

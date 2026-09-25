
import json
import sqlite3

from contextlib import closing
from pathlib import Path
from uuid import UUID

from jsonschema import (
    Draft202012Validator,
    FormatChecker
)

from src.closed_loop_simulator import parse_samples


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB = ROOT / "data" / "greenpulse.db"

SCHEMA = json.loads(
    (
        ROOT
        / "configs"
        / "closed_loop_response_schema_v1.json"
    ).read_text(encoding="utf-8-sig")
)

VALIDATOR = Draft202012Validator(
    SCHEMA,
    format_checker=FormatChecker()
)


def get_simulated_feedback(command_id, db_path=None):
    """
    Read a recorded synthetic closed-loop event.

    Returns None if no completed simulated
    follow-up exists for the command.

    Never communicates with physical hardware.
    """

    try:
        command_id = str(UUID(str(command_id)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid command_id.")

    db = (
        Path(db_path).resolve()
        if db_path is not None
        else DEFAULT_DB.resolve()
    )

    if not db.is_file():
        raise FileNotFoundError(
            "Audit database not found."
        )

    # SQLite read-only access.
    with closing(
        sqlite3.connect(
            db.as_uri() + "?mode=ro",
            uri=True,
            timeout=5
        )
    ) as conn:

        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT
                f.command_id,
                f.test_observation_id,
                f.plant_id,
                f.pre_samples_json,
                f.post_samples_json,
                f.moisture_before_pct,
                f.moisture_after_pct,
                f.synthetic_delta_pct_points,
                f.actuator_status,
                f.data_origin,
                f.physical_actuation
                    AS followup_physical,
                f.real_intervention_verified,
                f.measured_water_ml,
                f.recorded_at_utc,

                a.command_json,
                a.result_json,
                a.status AS audit_status,
                a.origin,
                a.simulated AS audit_simulated,
                a.physical_actuation
                    AS audit_physical

            FROM simulated_followup_events f

            JOIN simulated_actuator_events a
              ON a.command_id = f.command_id

            WHERE f.command_id = ?
            """,
            (command_id,)
        ).fetchone()

    if row is None:
        return None

    record = dict(row)

    command = json.loads(
        record["command_json"]
    )

    ack = json.loads(
        record["result_json"]
    )

    # Independently verify matching audit records.
    if not (
        record["command_id"] == command_id
        == command.get("command_id")
        == ack.get("command_id")

        and record["test_observation_id"]
        == command.get("observation_id")
        == ack.get("observation_id")

        and record["plant_id"]
        == command.get("plant_id")
        == ack.get("plant_id")

        and command.get("mode")
        == "SIMULATION_ONLY"

        and command.get("origin")
        == "TEST_HARNESS"

        and command.get("test_only") is True

        and command.get("action")
        == "IRRIGATION_TEST"

        and command.get("target")
        == "MAIN_IRRIGATION_PUMP"

        and record["origin"]
        == "TEST_HARNESS"

        and record["data_origin"]
        == "SYNTHETIC_FIXTURE"

        and record["audit_status"]
        == record["actuator_status"]
        == ack.get("status")
        == "SIMULATED_EXECUTED"

        and record["audit_simulated"] == 1
        and record["audit_physical"] == 0
        and record["followup_physical"] == 0

        and record["real_intervention_verified"] == 0
        and record["measured_water_ml"] is None

        and ack.get("simulated") is True
        and ack.get("physical_actuation") is False
        and ack.get("real_hardware_ack") is None
    ):
        raise ValueError(
            "Inconsistent simulated audit evidence."
        )

    # Validate original synthetic measurements.
    pre = parse_samples(
        json.loads(record["pre_samples_json"]),
        minimum=3
    )

    post = parse_samples(
        json.loads(record["post_samples_json"]),
        minimum=2
    )

    before = float(
        record["moisture_before_pct"]
    )

    after = float(
        record["moisture_after_pct"]
    )

    delta = float(
        record["synthetic_delta_pct_points"]
    )

    if not (
        before == pre[-1][1]
        and after == post[-1][1]
        and abs(
            delta - round(after - before, 4)
        ) < 0.00001
    ):
        raise ValueError(
            "Stored feedback does not match samples."
        )

    response = {
        "schema_version": "0.1.0",
        "mode": "SIMULATION_ONLY",
        "status": "SIMULATED_FEEDBACK_RECORDED",
        "data_origin": "SYNTHETIC_FIXTURE",

        "command_id": command_id,

        "observation_id": (
            record["test_observation_id"]
        ),

        "plant_id": record["plant_id"],

        "actuator_status": (
            "SIMULATED_EXECUTED"
        ),

        "moisture_before_pct": before,
        "moisture_after_pct": after,
        "synthetic_delta_pct_points": delta,

        "water_stress_risk_before": None,
        "water_stress_risk_after": None,

        "measured_water_ml": None,
        "real_hardware_ack": None,

        "physical_actuation": False,
        "real_intervention_verified": False,
        "operational_effectiveness_verified": False,

        "recorded_at_utc": (
            record["recorded_at_utc"]
        )
    }

    VALIDATOR.validate(response)

    return response

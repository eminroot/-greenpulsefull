
import json
import math
import sqlite3

from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.actuator_audit import (
    initialize_actuator_audit,
    safe_connection
)

from src.simulated_irrigation_flow import (
    run_simulated_irrigation_flow
)


MODULE_VERSION = "0.1.0"


def parse_samples(samples, minimum=1):
    """Validate strictly synthetic sensor observations."""

    if (
        not isinstance(samples, list)
        or not minimum <= len(samples) <= 20
    ):
        raise ValueError("Invalid synthetic sample count.")

    parsed = []

    for sample in samples:
        if (
            not isinstance(sample, dict)
            or set(sample) != {
                "timestamp",
                "soil_moisture_pct",
                "source"
            }
            or sample["source"] != "SIMULATED"
        ):
            raise ValueError("Invalid synthetic sample.")

        value = sample["soil_moisture_pct"]

        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not 0 <= value <= 100
        ):
            raise ValueError("Invalid moisture value.")

        timestamp = datetime.fromisoformat(
            sample["timestamp"]
        )

        if timestamp.tzinfo is None:
            raise ValueError("Timezone is required.")

        parsed.append((timestamp, float(value)))

    if any(
        current[0] <= previous[0]
        for previous, current in zip(
            parsed,
            parsed[1:]
        )
    ):
        raise ValueError(
            "Synthetic observations are not chronological."
        )

    return parsed


def create_feedback_table(db):
    with safe_connection(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS
            simulated_followup_events (
                command_id TEXT PRIMARY KEY
                    REFERENCES simulated_actuator_events(command_id),

                test_observation_id TEXT NOT NULL,
                plant_id TEXT NOT NULL,

                pre_samples_json TEXT NOT NULL,
                post_samples_json TEXT NOT NULL,

                moisture_before_pct REAL NOT NULL,
                moisture_after_pct REAL NOT NULL,
                synthetic_delta_pct_points REAL NOT NULL,

                actuator_status TEXT NOT NULL
                    CHECK(actuator_status = 'SIMULATED_EXECUTED'),

                data_origin TEXT NOT NULL
                    CHECK(data_origin = 'SYNTHETIC_FIXTURE'),

                physical_actuation INTEGER NOT NULL
                    CHECK(physical_actuation = 0),

                real_intervention_verified INTEGER NOT NULL
                    CHECK(real_intervention_verified = 0),

                measured_water_ml REAL
                    CHECK(measured_water_ml IS NULL),

                recorded_at_utc TEXT NOT NULL
            )
        """)


def run_simulated_closed_loop(
    payload,
    followup_samples,
    scenario="SUCCESS",
    db_path=None
):
    """
    End-to-end software-only closed-loop test.

    Never communicates with physical equipment.
    Synthetic sensor changes are NOT evidence
    of real plant recovery or water savings.
    """

    # Validate the proposed follow-up BEFORE
    # generating a simulated actuator command.
    post = parse_samples(
        followup_samples,
        minimum=2
    )

    if not isinstance(payload, dict):
        raise ValueError("Invalid test payload.")

    pre = parse_samples(
        payload.get("sensor_samples"),
        minimum=3
    )

    if post[0][0] <= pre[-1][0]:
        raise ValueError(
            "Follow-up must occur after baseline."
        )

    # Both operations are restricted to
    # development-only simulation modules.
    db = initialize_actuator_audit(db_path)

    flow = run_simulated_irrigation_flow(
        payload,
        scenario=scenario,
        db_path=db
    )

    ack = flow.get("simulated_ack")
    command = flow.get("command")

    # Failure, timeout and blocked decisions
    # must never produce a completed feedback record.
    if (
        not isinstance(ack, dict)
        or not isinstance(command, dict)
        or ack.get("status") != "SIMULATED_EXECUTED"
    ):
        return {
            "module_version": MODULE_VERSION,
            "status": "SIMULATED_NO_FOLLOWUP",
            "actuator_status": (
                ack.get("status")
                if isinstance(ack, dict)
                else None
            ),
            "feedback_recorded": False,
            "command_id": (
                command.get("command_id")
                if isinstance(command, dict)
                else None
            ),
            "physical_actuation": False,
            "water_stress_risk_before": None,
            "water_stress_risk_after": None,
            "measured_water_ml": None
        }

    if (
        ack.get("physical_actuation") is not False
        or ack.get("real_hardware_ack") is not None
        or ack.get("simulated") is not True
    ):
        raise ValueError("Unsafe actuator result.")

    # Independently verify that the simulator
    # actually logged the matching command and result.
    with safe_connection(db) as conn:
        row = conn.execute(
            """
            SELECT
                command_json,
                result_json,
                status,
                origin,
                simulated,
                physical_actuation,
                logged_at_utc
            FROM simulated_actuator_events
            WHERE command_id = ?
            """,
            (command["command_id"],)
        ).fetchone()

    if row is None:
        raise ValueError("Actuator audit evidence missing.")

    if (
        json.loads(row[0]) != command
        or json.loads(row[1]) != ack
        or row[2] != "SIMULATED_EXECUTED"
        or row[3] != "TEST_HARNESS"
        or row[4] != 1
        or row[5] != 0
    ):
        raise ValueError("Actuator audit mismatch.")

    action_time = datetime.fromisoformat(row[6])

    if action_time.tzinfo is None:
        raise ValueError("Invalid audit timestamp.")

    # This timing constraint belongs ONLY
    # to the synthetic test scenario.
    if (
        pre[-1][0] >= action_time
        or post[0][0] <= action_time
        or post[-1][0]
        > action_time + timedelta(minutes=30)
    ):
        raise ValueError(
            "Invalid synthetic intervention timeline."
        )

    before = pre[-1][1]
    after = post[-1][1]

    # This is a descriptive comparison of
    # invented fixture values, NOT a causal
    # estimate of irrigation effectiveness.
    delta = round(after - before, 4)

    create_feedback_table(db)

    with safe_connection(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute(
            """
            INSERT INTO simulated_followup_events (
                command_id,
                test_observation_id,
                plant_id,
                pre_samples_json,
                post_samples_json,
                moisture_before_pct,
                moisture_after_pct,
                synthetic_delta_pct_points,
                actuator_status,
                data_origin,
                physical_actuation,
                real_intervention_verified,
                measured_water_ml,
                recorded_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command["command_id"],
                command["observation_id"],
                command["plant_id"],
                json.dumps(
                    payload["sensor_samples"],
                    sort_keys=True
                ),
                json.dumps(
                    followup_samples,
                    sort_keys=True
                ),
                before,
                after,
                delta,
                "SIMULATED_EXECUTED",
                "SYNTHETIC_FIXTURE",
                0,
                0,
                None,
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
        )

    return {
        "module_version": MODULE_VERSION,
        "status": "SIMULATED_FEEDBACK_RECORDED",
        "command_id": command["command_id"],
        "plant_id": command["plant_id"],
        "actuator_status": "SIMULATED_EXECUTED",
        "feedback_recorded": True,
        "data_origin": "SYNTHETIC_FIXTURE",
        "moisture_before_pct": before,
        "moisture_after_pct": after,
        "synthetic_delta_pct_points": delta,
        "physical_actuation": False,
        "real_intervention_verified": False,
        "water_stress_risk_before": None,
        "water_stress_risk_after": None,
        "measured_water_ml": None
    }

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping, Optional

import json
import sqlite3


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB = (
    ROOT
    / "data"
    / "greenpulse.db"
)

SCHEDULER_SCHEMA_VERSION = (
    "greenpulse.closed_loop_followup_scheduler.v1"
)

VALID_PLAN_STATUSES = {
    "SYNTHETIC_FOLLOWUP_PLANNED",
    "FOLLOWUP_PLANNED",
}


@contextmanager
def safe_connection(
    db: Path,
):

    conn = sqlite3.connect(
        db,
        timeout=10,
    )

    try:

        with conn:

            yield conn

    finally:

        conn.close()


def initialize_followup_scheduler(
    db_path: Optional[Any] = None,
) -> Path:

    db = (
        Path(
            db_path
        )
        if db_path
        is not None
        else DEFAULT_DB
    )


    if not db.parent.exists():

        raise FileNotFoundError(
            "Database directory does not exist."
        )


    with safe_connection(
        db
    ) as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS
            closed_loop_followup_schedule (
                command_id TEXT PRIMARY KEY,
                plant_id TEXT NOT NULL,
                followup_due_at TEXT NOT NULL,
                action_timestamp TEXT NOT NULL,
                delay_seconds REAL NOT NULL
                    CHECK(delay_seconds > 0),
                test_only INTEGER NOT NULL
                    CHECK(test_only IN (0, 1)),
                real_intervention_verified INTEGER NOT NULL
                    CHECK(real_intervention_verified IN (0, 1)),
                schedule_state TEXT NOT NULL
                    CHECK(
                        schedule_state IN (
                            'PENDING',
                            'CONSUMED',
                            'CANCELLED'
                        )
                    ),
                plan_json TEXT NOT NULL,
                scheduler_schema_version TEXT NOT NULL,
                scheduled_at_utc TEXT NOT NULL
            )
            """
        )


    return db


def schedule_followup(
    plan: Mapping[
        str,
        Any,
    ],
    *,
    db_path: Optional[Any] = None,
) -> dict[str, Any]:

    if not isinstance(
        plan,
        Mapping,
    ):

        raise ValueError(
            "plan must be a mapping."
        )


    if (
        plan.get(
            "schema_version"
        )
        != "greenpulse.closed_loop_followup_plan.v1"
    ):

        raise ValueError(
            "Unsupported follow-up plan schema."
        )


    if (
        plan.get(
            "status"
        )
        not in VALID_PLAN_STATUSES
    ):

        raise ValueError(
            "Only planned follow-ups can be scheduled."
        )


    command_id = plan.get(
        "command_id"
    )

    plant_id = plan.get(
        "plant_id"
    )

    followup_due_at = plan.get(
        "followup_due_at"
    )

    action_timestamp = plan.get(
        "action_timestamp"
    )

    delay_seconds = plan.get(
        "delay_seconds"
    )


    if not all(
        isinstance(
            value,
            str,
        )
        and value.strip()
        for value in (
            command_id,
            plant_id,
            followup_due_at,
            action_timestamp,
        )
    ):

        raise ValueError(
            "Required follow-up identity/timestamp fields missing."
        )


    if (
        isinstance(
            delay_seconds,
            bool,
        )
        or not isinstance(
            delay_seconds,
            (int, float),
        )
        or float(
            delay_seconds
        )
        <= 0.0
    ):

        raise ValueError(
            "Invalid follow-up delay."
        )


    test_only = (
        plan.get(
            "test_only"
        )
        is True
    )

    real_verified = (
        plan.get(
            "real_intervention_verified"
        )
        is True
    )


    if test_only:

        if real_verified:

            raise ValueError(
                "Synthetic follow-up cannot claim "
                "verified real intervention."
            )

    else:

        if not real_verified:

            raise ValueError(
                "Operational follow-up scheduling requires "
                "verified real intervention."
            )


    from datetime import (
        datetime,
        timezone,
    )


    db = initialize_followup_scheduler(
        db_path
    )

    scheduled_at = datetime.now(
        timezone.utc
    ).isoformat()


    with safe_connection(
        db
    ) as conn:

        conn.execute(
            """
            INSERT INTO closed_loop_followup_schedule (
                command_id,
                plant_id,
                followup_due_at,
                action_timestamp,
                delay_seconds,
                test_only,
                real_intervention_verified,
                schedule_state,
                plan_json,
                scheduler_schema_version,
                scheduled_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command_id,
                plant_id,
                followup_due_at,
                action_timestamp,
                float(
                    delay_seconds
                ),
                int(
                    test_only
                ),
                int(
                    real_verified
                ),
                "PENDING",
                json.dumps(
                    dict(
                        plan
                    ),
                    sort_keys=True,
                    allow_nan=False,
                ),
                SCHEDULER_SCHEMA_VERSION,
                scheduled_at,
            ),
        )


    return {
        "schema_version":
            SCHEDULER_SCHEMA_VERSION,

        "command_id":
            command_id,

        "plant_id":
            plant_id,

        "followup_due_at":
            followup_due_at,

        "schedule_state":
            "PENDING",

        "scheduled":
            True,

        "test_only":
            test_only,

        "real_intervention_verified":
            real_verified,

        "scheduler_executes_inference":
            False,

        "scheduler_dispatches_hardware":
            False,

        "physical_action_triggered":
            False,
    }


def get_pending_followups(
    *,
    db_path: Optional[Any] = None,
) -> list[dict[str, Any]]:

    db = (
        Path(
            db_path
        ).resolve()
        if db_path
        is not None
        else DEFAULT_DB.resolve()
    )


    if not db.is_file():

        return []


    conn = sqlite3.connect(
        db.as_uri()
        + "?mode=ro",
        uri=True,
        timeout=5,
    )


    try:

        conn.row_factory = (
            sqlite3.Row
        )


        table_exists = (
            conn.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type='table'
                  AND name='closed_loop_followup_schedule'
                """
            ).fetchone()
            is not None
        )


        if not table_exists:

            return []


        rows = conn.execute(
            """
            SELECT
                command_id,
                plant_id,
                followup_due_at,
                action_timestamp,
                delay_seconds,
                test_only,
                real_intervention_verified,
                schedule_state,
                scheduled_at_utc
            FROM closed_loop_followup_schedule
            WHERE schedule_state = 'PENDING'
            ORDER BY
                followup_due_at ASC,
                command_id ASC
            """
        ).fetchall()


        return [
            {
                **dict(
                    row
                ),

                "test_only":
                    bool(
                        row[
                            "test_only"
                        ]
                    ),

                "real_intervention_verified":
                    bool(
                        row[
                            "real_intervention_verified"
                        ]
                    ),
            }
            for row in rows
        ]


    finally:

        conn.close()


def mark_followup_consumed(
    command_id: str,
    *,
    db_path: Optional[Any] = None,
) -> bool:

    if (
        not isinstance(
            command_id,
            str,
        )
        or not command_id.strip()
    ):

        raise ValueError(
            "command_id is required."
        )


    db = (
        Path(
            db_path
        )
        if db_path
        is not None
        else DEFAULT_DB
    )


    if not db.is_file():

        return False


    with safe_connection(
        db
    ) as conn:

        cursor = conn.execute(
            """
            UPDATE closed_loop_followup_schedule
            SET schedule_state = 'CONSUMED'
            WHERE command_id = ?
              AND schedule_state = 'PENDING'
            """,
            (
                command_id,
            ),
        )


        return (
            cursor.rowcount
            == 1
        )
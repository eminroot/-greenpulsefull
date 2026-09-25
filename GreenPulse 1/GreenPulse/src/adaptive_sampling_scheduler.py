from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping, Optional

import sqlite3


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB = (
    ROOT
    / "data"
    / "greenpulse.db"
)

SCHEDULER_SCHEMA_VERSION = (
    "greenpulse.adaptive_sampling_scheduler.v1"
)


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


def initialize_sampling_scheduler(
    db_path: Optional[Any] = None,
) -> Path:

    db = (
        Path(
            db_path
        )
        if db_path is not None
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
            adaptive_sampling_schedule (
                decision_id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                sampling_level TEXT NOT NULL
                    CHECK(
                        sampling_level IN (
                            'STABLE_HEALTHY',
                            'NORMAL',
                            'ELEVATED',
                            'HIGH'
                        )
                    ),
                interval_seconds REAL NOT NULL
                    CHECK(interval_seconds > 0),
                next_observation_at TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                policy_status TEXT NOT NULL,
                schedule_state TEXT NOT NULL
                    CHECK(
                        schedule_state IN (
                            'PENDING',
                            'SUPERSEDED',
                            'CONSUMED'
                        )
                    ),
                created_at_utc TEXT NOT NULL
            )
            """
        )


    return db


def schedule_sampling_decision(
    decision: Mapping[
        str,
        Any,
    ],
    *,
    db_path: Optional[Any] = None,
) -> dict[str, Any]:

    if not isinstance(
        decision,
        Mapping,
    ):

        raise ValueError(
            "decision must be a mapping."
        )


    if (
        decision.get(
            "schema_version"
        )
        != "greenpulse.adaptive_sampling_decision.v1"
    ):

        raise ValueError(
            "Unsupported sampling decision schema."
        )


    if (
        decision.get(
            "policy_status"
        )
        != "DEVELOPMENT_ONLY_UNVALIDATED"
    ):

        raise ValueError(
            "Unsupported sampling policy status."
        )


    required_strings = (
        "decision_id",
        "observation_id",
        "plant_id",
        "sampling_level",
        "next_observation_at",
        "policy_version",
    )


    for field in required_strings:

        value = decision.get(
            field
        )

        if (
            not isinstance(
                value,
                str,
            )
            or not value.strip()
        ):

            raise ValueError(
                f"{field} is required."
            )


    interval = decision.get(
        "interval_seconds"
    )


    if (
        isinstance(
            interval,
            bool,
        )
        or not isinstance(
            interval,
            (int, float),
        )
        or float(
            interval
        )
        <= 0
    ):

        raise ValueError(
            "Invalid interval_seconds."
        )


    from datetime import (
        datetime,
        timezone,
    )


    db = initialize_sampling_scheduler(
        db_path
    )


    created_at = datetime.now(
        timezone.utc
    ).isoformat()


    with safe_connection(
        db
    ) as conn:

        # A newer adaptive decision replaces the
        # previous pending cadence for the same plant.
        conn.execute(
            """
            UPDATE adaptive_sampling_schedule
            SET schedule_state = 'SUPERSEDED'
            WHERE plant_id = ?
              AND schedule_state = 'PENDING'
            """,
            (
                decision[
                    "plant_id"
                ],
            ),
        )


        conn.execute(
            """
            INSERT INTO adaptive_sampling_schedule (
                decision_id,
                observation_id,
                plant_id,
                sampling_level,
                interval_seconds,
                next_observation_at,
                policy_version,
                policy_status,
                schedule_state,
                created_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision[
                    "decision_id"
                ],
                decision[
                    "observation_id"
                ],
                decision[
                    "plant_id"
                ],
                decision[
                    "sampling_level"
                ],
                float(
                    interval
                ),
                decision[
                    "next_observation_at"
                ],
                decision[
                    "policy_version"
                ],
                decision[
                    "policy_status"
                ],
                "PENDING",
                created_at,
            ),
        )


    return {
        "schema_version":
            SCHEDULER_SCHEMA_VERSION,

        "decision_id":
            decision[
                "decision_id"
            ],

        "plant_id":
            decision[
                "plant_id"
            ],

        "sampling_level":
            decision[
                "sampling_level"
            ],

        "interval_seconds":
            float(
                interval
            ),

        "next_observation_at":
            decision[
                "next_observation_at"
            ],

        "schedule_state":
            "PENDING",

        "scheduled":
            True,

        "camera_triggered":
            False,

        "image_captured":
            False,

        "inference_triggered":
            False,
    }


def get_pending_sampling_schedule(
    *,
    db_path: Optional[Any] = None,
) -> list[dict[str, Any]]:

    db = (
        Path(
            db_path
        ).resolve()
        if db_path is not None
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


        exists = (
            conn.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type='table'
                  AND name='adaptive_sampling_schedule'
                """
            ).fetchone()
            is not None
        )


        if not exists:

            return []


        rows = conn.execute(
            """
            SELECT
                decision_id,
                observation_id,
                plant_id,
                sampling_level,
                interval_seconds,
                next_observation_at,
                policy_version,
                policy_status,
                schedule_state,
                created_at_utc
            FROM adaptive_sampling_schedule
            WHERE schedule_state = 'PENDING'
            ORDER BY
                next_observation_at ASC,
                plant_id ASC
            """
        ).fetchall()


        return [
            dict(
                row
            )
            for row in rows
        ]


    finally:

        conn.close()


def mark_sampling_schedule_consumed(
    decision_id: str,
    *,
    db_path: Optional[Any] = None,
) -> bool:

    if (
        not isinstance(
            decision_id,
            str,
        )
        or not decision_id.strip()
    ):

        raise ValueError(
            "decision_id is required."
        )


    db = (
        Path(
            db_path
        )
        if db_path is not None
        else DEFAULT_DB
    )


    if not db.is_file():

        return False


    with safe_connection(
        db
    ) as conn:

        cursor = conn.execute(
            """
            UPDATE adaptive_sampling_schedule
            SET schedule_state = 'CONSUMED'
            WHERE decision_id = ?
              AND schedule_state = 'PENDING'
            """,
            (
                decision_id,
            ),
        )


        return (
            cursor.rowcount
            == 1
        )
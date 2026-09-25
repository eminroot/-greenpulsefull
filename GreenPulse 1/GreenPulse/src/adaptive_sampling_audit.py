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

AUDIT_SCHEMA_VERSION = (
    "greenpulse.adaptive_sampling_audit.v1"
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


def initialize_sampling_audit(
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
            adaptive_sampling_decisions (
                decision_id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                observation_timestamp TEXT NOT NULL,
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
                reason_codes_json TEXT NOT NULL,
                input_summary_json TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                audit_schema_version TEXT NOT NULL,
                stored_at_utc TEXT NOT NULL
            )
            """
        )


    return db


def store_sampling_decision(
    decision: Mapping[
        str,
        Any,
    ],
    *,
    db_path: Optional[Any] = None,
) -> str:

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
            "Only current development policy decisions "
            "may be stored by this audit layer."
        )


    required_strings = (
        "decision_id",
        "observation_id",
        "plant_id",
        "observation_timestamp",
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


    reason_codes = decision.get(
        "reason_codes"
    )

    input_summary = decision.get(
        "input_summary"
    )


    if (
        not isinstance(
            reason_codes,
            list,
        )
        or not all(
            isinstance(
                item,
                str,
            )
            and item.strip()
            for item in reason_codes
        )
    ):

        raise ValueError(
            "reason_codes must be a string list."
        )


    if not isinstance(
        input_summary,
        Mapping,
    ):

        raise ValueError(
            "input_summary must be a mapping."
        )


    from datetime import (
        datetime,
        timezone,
    )


    db = initialize_sampling_audit(
        db_path
    )


    stored_at = datetime.now(
        timezone.utc
    ).isoformat()


    with safe_connection(
        db
    ) as conn:

        conn.execute(
            """
            INSERT INTO adaptive_sampling_decisions (
                decision_id,
                observation_id,
                plant_id,
                observation_timestamp,
                sampling_level,
                interval_seconds,
                next_observation_at,
                policy_version,
                policy_status,
                reason_codes_json,
                input_summary_json,
                decision_json,
                audit_schema_version,
                stored_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    "observation_timestamp"
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
                json.dumps(
                    reason_codes,
                    sort_keys=True,
                    allow_nan=False,
                ),
                json.dumps(
                    dict(
                        input_summary
                    ),
                    sort_keys=True,
                    allow_nan=False,
                ),
                json.dumps(
                    dict(
                        decision
                    ),
                    sort_keys=True,
                    allow_nan=False,
                ),
                AUDIT_SCHEMA_VERSION,
                stored_at,
            ),
        )


    return str(
        decision[
            "decision_id"
        ]
    )


def get_recent_sampling_decisions(
    *,
    limit: int = 20,
    db_path: Optional[Any] = None,
) -> list[dict[str, Any]]:

    if (
        type(
            limit
        )
        is not int
        or not 1
        <= limit
        <= 100
    ):

        raise ValueError(
            "limit must be in [1, 100]."
        )


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
                  AND name='adaptive_sampling_decisions'
                """
            ).fetchone()
            is not None
        )


        if not exists:

            return []


        rows = conn.execute(
            """
            SELECT
                decision_json,
                stored_at_utc
            FROM adaptive_sampling_decisions
            ORDER BY
                stored_at_utc DESC,
                decision_id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        ).fetchall()


        result = []


        for row in rows:

            payload = json.loads(
                row[
                    "decision_json"
                ]
            )


            payload[
                "audit"
            ] = {
                "schema_version":
                    AUDIT_SCHEMA_VERSION,

                "stored_at_utc":
                    row[
                        "stored_at_utc"
                    ],
            }


            result.append(
                payload
            )


        return result


    finally:

        conn.close()


def get_sampling_decision(
    decision_id: str,
    *,
    db_path: Optional[Any] = None,
) -> Optional[dict[str, Any]]:

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
        ).resolve()
        if db_path is not None
        else DEFAULT_DB.resolve()
    )


    if not db.is_file():

        return None


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
                  AND name='adaptive_sampling_decisions'
                """
            ).fetchone()
            is not None
        )


        if not exists:

            return None


        row = conn.execute(
            """
            SELECT
                decision_json,
                stored_at_utc
            FROM adaptive_sampling_decisions
            WHERE decision_id = ?
            LIMIT 1
            """,
            (
                decision_id,
            ),
        ).fetchone()


        if row is None:

            return None


        payload = json.loads(
            row[
                "decision_json"
            ]
        )


        payload[
            "audit"
        ] = {
            "schema_version":
                AUDIT_SCHEMA_VERSION,

            "stored_at_utc":
                row[
                    "stored_at_utc"
                ],
        }


        return payload


    finally:

        conn.close()
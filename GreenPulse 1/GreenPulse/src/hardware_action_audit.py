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
    "greenpulse.hardware_action_state_audit.v1"
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


def initialize_action_state_audit(
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
            hardware_action_states (
                command_id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                target TEXT,
                action_state TEXT NOT NULL
                    CHECK(
                        action_state IN (
                            'EXECUTED',
                            'REJECTED',
                            'FAILED',
                            'TIMEOUT'
                        )
                    ),
                error_code TEXT,
                state_timestamp TEXT NOT NULL,
                ack_origin TEXT NOT NULL,
                source_status TEXT NOT NULL,
                simulated INTEGER NOT NULL
                    CHECK(
                        simulated IN (0, 1)
                    ),
                real_hardware_ack INTEGER NOT NULL
                    CHECK(
                        real_hardware_ack IN (0, 1)
                    ),
                real_hardware_ack_validated INTEGER NOT NULL
                    CHECK(
                        real_hardware_ack_validated = 0
                    ),
                physical_actuation INTEGER,
                canonical_json TEXT NOT NULL,
                audit_schema_version TEXT NOT NULL,
                stored_at_utc TEXT NOT NULL
            )
            """
        )


    return db


def store_action_state(
    action_state: Mapping[
        str,
        Any,
    ],
    *,
    db_path: Optional[Any] = None,
) -> str:

    if not isinstance(
        action_state,
        Mapping,
    ):

        raise ValueError(
            "action_state must be a mapping."
        )


    if (
        action_state.get(
            "schema_version"
        )
        != "greenpulse.hardware_action_state.v1"
    ):

        raise ValueError(
            "Unsupported action-state schema."
        )


    if (
        action_state.get(
            "real_hardware_ack_validated"
        )
        is not False
    ):

        raise ValueError(
            "Only unvalidated ACK state is currently supported."
        )


    if (
        action_state.get(
            "physical_actuation"
        )
        is True
    ):

        raise ValueError(
            "Physical actuation evidence is not accepted."
        )


    if (
        action_state.get(
            "audit_storage_allowed"
        )
        is not True
    ):

        raise ValueError(
            "Action state is not approved for audit storage."
        )


    command_id = action_state.get(
        "command_id"
    )

    observation_id = action_state.get(
        "observation_id"
    )

    plant_id = action_state.get(
        "plant_id"
    )

    state = action_state.get(
        "action_state"
    )


    if not all(
        isinstance(
            value,
            str,
        )
        and value.strip()
        for value in (
            command_id,
            observation_id,
            plant_id,
            state,
        )
    ):

        raise ValueError(
            "Required action-state identity fields missing."
        )


    db = initialize_action_state_audit(
        db_path
    )


    from datetime import (
        datetime,
        timezone,
    )


    stored_at = datetime.now(
        timezone.utc
    ).isoformat()


    physical = (
        action_state.get(
            "physical_actuation"
        )
    )


    physical_db = (
        None
        if physical is None
        else int(
            physical
        )
    )


    with safe_connection(
        db
    ) as conn:

        conn.execute(
            """
            INSERT INTO hardware_action_states (
                command_id,
                observation_id,
                plant_id,
                target,
                action_state,
                error_code,
                state_timestamp,
                ack_origin,
                source_status,
                simulated,
                real_hardware_ack,
                real_hardware_ack_validated,
                physical_actuation,
                canonical_json,
                audit_schema_version,
                stored_at_utc
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                command_id,
                observation_id,
                plant_id,
                action_state.get(
                    "target"
                ),
                state,
                action_state.get(
                    "error_code"
                ),
                action_state.get(
                    "state_timestamp"
                ),
                action_state.get(
                    "ack_origin"
                ),
                action_state.get(
                    "source_status"
                ),
                int(
                    action_state.get(
                        "simulated"
                    )
                    is True
                ),
                int(
                    action_state.get(
                        "real_hardware_ack"
                    )
                    is True
                ),
                0,
                physical_db,
                json.dumps(
                    dict(
                        action_state
                    ),
                    sort_keys=True,
                    allow_nan=False,
                ),
                AUDIT_SCHEMA_VERSION,
                stored_at,
            ),
        )


    return str(
        command_id
    )


def get_recent_action_states(
    *,
    limit: int = 20,
    db_path: Optional[Any] = None,
) -> list[dict[str, Any]]:

    if (
        type(
            limit
        )
        is not int
        or not (
            1 <= limit <= 100
        )
    ):

        raise ValueError(
            "limit must be in [1, 100]."
        )


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


    connection = sqlite3.connect(
        db.as_uri()
        + "?mode=ro",
        uri=True,
        timeout=5,
    )


    try:

        connection.row_factory = (
            sqlite3.Row
        )


        table_exists = (
            connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'hardware_action_states'
                """
            ).fetchone()
            is not None
        )


        if not table_exists:

            return []


        rows = connection.execute(
            """
            SELECT
                canonical_json,
                stored_at_utc
            FROM hardware_action_states
            ORDER BY
                stored_at_utc DESC,
                command_id DESC
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
                    "canonical_json"
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


    finally:

        connection.close()


    return result


def get_action_state_by_command_id(
    command_id: str,
    *,
    db_path: Optional[Any] = None,
) -> Optional[dict[str, Any]]:

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
        ).resolve()
        if db_path
        is not None
        else DEFAULT_DB.resolve()
    )


    if not db.is_file():

        return None


    connection = sqlite3.connect(
        db.as_uri()
        + "?mode=ro",
        uri=True,
        timeout=5,
    )


    try:

        connection.row_factory = (
            sqlite3.Row
        )


        table_exists = (
            connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'hardware_action_states'
                """
            ).fetchone()
            is not None
        )


        if not table_exists:

            return None


        row = connection.execute(
            """
            SELECT
                canonical_json,
                stored_at_utc
            FROM hardware_action_states
            WHERE command_id = ?
            LIMIT 1
            """,
            (
                command_id,
            ),
        ).fetchone()


        if row is None:

            return None


        payload = json.loads(
            row[
                "canonical_json"
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

        connection.close()
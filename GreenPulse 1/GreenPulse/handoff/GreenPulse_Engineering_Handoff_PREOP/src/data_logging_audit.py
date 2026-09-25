from __future__ import annotations

from typing import Any

import sqlite3


SCHEMA_VERSION = (
    "greenpulse.data_logging_audit.v1"
)


REQUIRED_TABLES = (
    "observations",
    "images",
    "predictions",
    "sensor_readings",
    "risk_scores",
    "forecasts",
    "decisions",
    "commands",
    "actions",
    "sustainability_metrics",
    "system_events",
    "model_versions",
)


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    crop TEXT
);

CREATE TABLE IF NOT EXISTS model_versions (
    model_version_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_sha256 TEXT,
    artifact_path TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS images (
    image_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    image_sha256 TEXT,
    captured_at TEXT,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id)
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    image_id TEXT,
    model_version_id TEXT NOT NULL,
    predicted_class TEXT,
    confidence REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id),
    FOREIGN KEY (image_id)
        REFERENCES images(image_id),
    FOREIGN KEY (model_version_id)
        REFERENCES model_versions(model_version_id)
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    sensor_reading_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    sensor_type TEXT,
    value REAL,
    unit TEXT,
    timestamp TEXT NOT NULL,
    validation_status TEXT,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id)
);

CREATE TABLE IF NOT EXISTS risk_scores (
    risk_score_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    model_version_id TEXT NOT NULL,
    risk_score REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id),
    FOREIGN KEY (model_version_id)
        REFERENCES model_versions(model_version_id)
);

CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    model_version_id TEXT NOT NULL,
    forecast_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id),
    FOREIGN KEY (model_version_id)
        REFERENCES model_versions(model_version_id)
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    risk_score_id TEXT NOT NULL,
    forecast_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id),
    FOREIGN KEY (risk_score_id)
        REFERENCES risk_scores(risk_score_id),
    FOREIGN KEY (forecast_id)
        REFERENCES forecasts(forecast_id)
);

CREATE TABLE IF NOT EXISTS commands (
    command_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    command_type TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id),
    FOREIGN KEY (decision_id)
        REFERENCES decisions(decision_id)
);

CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    command_id TEXT NOT NULL,
    action_state TEXT NOT NULL,
    ack_type TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (command_id)
        REFERENCES commands(command_id)
);

CREATE TABLE IF NOT EXISTS sustainability_metrics (
    metric_id TEXT PRIMARY KEY,
    observation_id TEXT,
    command_id TEXT,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_unit TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id),
    FOREIGN KEY (command_id)
        REFERENCES commands(command_id)
);

CREATE TABLE IF NOT EXISTS system_events (
    event_id TEXT PRIMARY KEY,
    observation_id TEXT,
    command_id TEXT,
    event_type TEXT NOT NULL,
    severity TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (observation_id)
        REFERENCES observations(observation_id),
    FOREIGN KEY (command_id)
        REFERENCES commands(command_id)
);
"""


def initialize_audit_schema(
    conn: sqlite3.Connection,
) -> None:

    if not isinstance(
        conn,
        sqlite3.Connection,
    ):

        raise ValueError(
            "conn must be sqlite3.Connection."
        )


    conn.executescript(
        SCHEMA_SQL
    )

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )


def audit_schema(
    conn: sqlite3.Connection,
) -> dict[str, Any]:

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()


    existing = {
        row[0]
        for row in rows
    }


    missing = [
        table
        for table in REQUIRED_TABLES
        if table not in existing
    ]


    columns = {}


    for table in REQUIRED_TABLES:

        if table not in existing:

            columns[
                table
            ] = []

            continue


        safe_table = table.replace(
            '"',
            '""',
        )

        info = conn.execute(
            f'PRAGMA table_info("{safe_table}")'
        ).fetchall()


        columns[
            table
        ] = [
            row[1]
            for row in info
        ]


    return {
        "schema_version":
            SCHEMA_VERSION,

        "required_table_count":
            len(
                REQUIRED_TABLES
            ),

        "present_required_table_count":
            (
                len(
                    REQUIRED_TABLES
                )
                - len(
                    missing
                )
            ),

        "missing_tables":
            missing,

        "all_required_tables_present":
            not missing,

        "columns":
            columns,

        "foreign_keys_enabled":
            bool(
                conn.execute(
                    "PRAGMA foreign_keys"
                ).fetchone()[
                    0
                ]
            ),
    }
from __future__ import annotations

from typing import Any

import sqlite3


SCHEMA_VERSION = (
    "greenpulse.command_trace.v1"
)


def _fetch_one(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
):

    cursor = conn.execute(
        sql,
        params,
    )

    row = cursor.fetchone()


    if row is None:

        return None


    names = [
        item[
            0
        ]
        for item
        in cursor.description
    ]


    return dict(
        zip(
            names,
            row,
        )
    )


def _fetch_all(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
):

    cursor = conn.execute(
        sql,
        params,
    )

    names = [
        item[
            0
        ]
        for item
        in cursor.description
    ]


    return [
        dict(
            zip(
                names,
                row,
            )
        )
        for row in cursor.fetchall()
    ]


def trace_command(
    conn: sqlite3.Connection,
    command_id: str,
) -> dict[str, Any]:

    if not isinstance(
        command_id,
        str,
    ) or not command_id.strip():

        raise ValueError(
            "command_id must be a non-empty string."
        )


    command_id = command_id.strip()


    command = _fetch_one(
        conn,
        """
        SELECT *
        FROM commands
        WHERE command_id = ?
        """,
        (
            command_id,
        ),
    )


    if command is None:

        raise KeyError(
            f"Unknown command_id: {command_id}"
        )


    observation_id = command[
        "observation_id"
    ]

    decision_id = command[
        "decision_id"
    ]


    observation = _fetch_one(
        conn,
        """
        SELECT *
        FROM observations
        WHERE observation_id = ?
        """,
        (
            observation_id,
        ),
    )


    images = _fetch_all(
        conn,
        """
        SELECT *
        FROM images
        WHERE observation_id = ?
        ORDER BY image_id
        """,
        (
            observation_id,
        ),
    )


    sensors = _fetch_all(
        conn,
        """
        SELECT *
        FROM sensor_readings
        WHERE observation_id = ?
        ORDER BY sensor_reading_id
        """,
        (
            observation_id,
        ),
    )


    predictions = _fetch_all(
        conn,
        """
        SELECT *
        FROM predictions
        WHERE observation_id = ?
        ORDER BY prediction_id
        """,
        (
            observation_id,
        ),
    )


    risk_scores = _fetch_all(
        conn,
        """
        SELECT *
        FROM risk_scores
        WHERE observation_id = ?
        ORDER BY risk_score_id
        """,
        (
            observation_id,
        ),
    )


    forecasts = _fetch_all(
        conn,
        """
        SELECT *
        FROM forecasts
        WHERE observation_id = ?
        ORDER BY forecast_id
        """,
        (
            observation_id,
        ),
    )


    decision = _fetch_one(
        conn,
        """
        SELECT *
        FROM decisions
        WHERE decision_id = ?
        """,
        (
            decision_id,
        ),
    )


    actions = _fetch_all(
        conn,
        """
        SELECT *
        FROM actions
        WHERE command_id = ?
        ORDER BY action_id
        """,
        (
            command_id,
        ),
    )


    sustainability_metrics = _fetch_all(
        conn,
        """
        SELECT *
        FROM sustainability_metrics
        WHERE command_id = ?
           OR observation_id = ?
        ORDER BY metric_id
        """,
        (
            command_id,
            observation_id,
        ),
    )


    system_events = _fetch_all(
        conn,
        """
        SELECT *
        FROM system_events
        WHERE command_id = ?
           OR observation_id = ?
        ORDER BY event_id
        """,
        (
            command_id,
            observation_id,
        ),
    )


    model_version_ids = set()


    for row in (
        predictions
        + risk_scores
        + forecasts
    ):

        value = row.get(
            "model_version_id"
        )


        if value:

            model_version_ids.add(
                value
            )


    model_versions = []


    if model_version_ids:

        ordered_ids = sorted(
            model_version_ids
        )

        placeholders = ",".join(
            "?"
            for _ in ordered_ids
        )

        model_versions = _fetch_all(
            conn,
            f"""
            SELECT *
            FROM model_versions
            WHERE model_version_id
                  IN ({placeholders})
            ORDER BY model_version_id
            """,
            tuple(
                ordered_ids
            ),
        )


    required_lineage = {
        "image":
            bool(
                images
            ),

        "sensor_data":
            bool(
                sensors
            ),

        "model_version":
            bool(
                model_versions
            ),

        "risk":
            bool(
                risk_scores
            ),

        "forecast":
            bool(
                forecasts
            ),

        "decision":
            decision is not None,
    }


    return {
        "schema_version":
            SCHEMA_VERSION,

        "command_id":
            command_id,

        "command":
            command,

        "observation":
            observation,

        "images":
            images,

        "sensor_readings":
            sensors,

        "predictions":
            predictions,

        "model_versions":
            model_versions,

        "risk_scores":
            risk_scores,

        "forecasts":
            forecasts,

        "decision":
            decision,

        "actions":
            actions,

        "sustainability_metrics":
            sustainability_metrics,

        "system_events":
            system_events,

        "required_lineage":
            required_lineage,

        "required_lineage_complete":
            all(
                required_lineage.values()
            ),
    }
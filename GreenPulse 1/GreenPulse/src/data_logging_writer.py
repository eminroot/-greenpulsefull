from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import sqlite3


SCHEMA_VERSION = (
    "greenpulse.audit_writer.v1"
)


def _require_mapping(
    bundle: Mapping[str, Any],
    key: str,
) -> dict[str, Any]:

    value = bundle.get(
        key
    )


    if not isinstance(
        value,
        Mapping,
    ):

        raise ValueError(
            f"{key} must be a mapping."
        )


    return dict(
        value
    )


def _require_list(
    bundle: Mapping[str, Any],
    key: str,
) -> list[dict[str, Any]]:

    value = bundle.get(
        key
    )


    if not isinstance(
        value,
        list,
    ):

        raise ValueError(
            f"{key} must be a list."
        )


    rows = []


    for item in value:

        if not isinstance(
            item,
            Mapping,
        ):

            raise ValueError(
                f"Every {key} item must be a mapping."
            )


        rows.append(
            dict(
                item
            )
        )


    return rows


def _validate_bundle(
    bundle: Mapping[str, Any],
) -> dict[str, Any]:

    if not isinstance(
        bundle,
        Mapping,
    ):

        raise ValueError(
            "bundle must be a mapping."
        )


    observation = _require_mapping(
        bundle,
        "observation",
    )

    decision = _require_mapping(
        bundle,
        "decision",
    )

    command = _require_mapping(
        bundle,
        "command",
    )


    model_versions = _require_list(
        bundle,
        "model_versions",
    )

    images = _require_list(
        bundle,
        "images",
    )

    predictions = _require_list(
        bundle,
        "predictions",
    )

    sensor_readings = _require_list(
        bundle,
        "sensor_readings",
    )

    risk_scores = _require_list(
        bundle,
        "risk_scores",
    )

    forecasts = _require_list(
        bundle,
        "forecasts",
    )


    actions = _require_list(
        bundle,
        "actions",
    )

    sustainability_metrics = _require_list(
        bundle,
        "sustainability_metrics",
    )

    system_events = _require_list(
        bundle,
        "system_events",
    )


    observation_id = observation.get(
        "observation_id"
    )


    if (
        not isinstance(
            observation_id,
            str,
        )
        or not observation_id.strip()
    ):

        raise ValueError(
            "observation_id missing."
        )


    observation_id = (
        observation_id.strip()
    )


    if not model_versions:

        raise ValueError(
            "At least one model_version is required."
        )


    if not images:

        raise ValueError(
            "At least one image is required."
        )


    if not predictions:

        raise ValueError(
            "At least one prediction is required."
        )


    if not sensor_readings:

        raise ValueError(
            "At least one sensor_reading is required."
        )


    if not risk_scores:

        raise ValueError(
            "At least one risk_score is required."
        )


    if not forecasts:

        raise ValueError(
            "At least one forecast is required."
        )


    observation_scoped = (
        images
        + predictions
        + sensor_readings
        + risk_scores
        + forecasts
        + [
            decision,
            command,
        ]
    )


    for row in observation_scoped:

        if (
            row.get(
                "observation_id"
            )
            != observation_id
        ):

            raise ValueError(
                "Cross-observation lineage detected."
            )


    image_ids = {
        row.get(
            "image_id"
        )
        for row in images
    }


    model_version_ids = {
        row.get(
            "model_version_id"
        )
        for row in model_versions
    }


    risk_ids = {
        row.get(
            "risk_score_id"
        )
        for row in risk_scores
    }


    forecast_ids = {
        row.get(
            "forecast_id"
        )
        for row in forecasts
    }


    for prediction in predictions:

        if (
            prediction.get(
                "image_id"
            )
            not in image_ids
        ):

            raise ValueError(
                "Prediction references unknown image_id."
            )


        if (
            prediction.get(
                "model_version_id"
            )
            not in model_version_ids
        ):

            raise ValueError(
                "Prediction references unknown model_version_id."
            )


    for row in (
        risk_scores
        + forecasts
    ):

        if (
            row.get(
                "model_version_id"
            )
            not in model_version_ids
        ):

            raise ValueError(
                "Risk/forecast references unknown model_version_id."
            )


    if (
        decision.get(
            "risk_score_id"
        )
        not in risk_ids
    ):

        raise ValueError(
            "Decision references unknown risk_score_id."
        )


    if (
        decision.get(
            "forecast_id"
        )
        not in forecast_ids
    ):

        raise ValueError(
            "Decision references unknown forecast_id."
        )


    if (
        command.get(
            "decision_id"
        )
        != decision.get(
            "decision_id"
        )
    ):

        raise ValueError(
            "Command decision_id linkage invalid."
        )


    command_id = command.get(
        "command_id"
    )


    for action in actions:

        if (
            action.get(
                "command_id"
            )
            != command_id
        ):

            raise ValueError(
                "Action command_id linkage invalid."
            )


    for row in (
        sustainability_metrics
        + system_events
    ):

        row_observation = row.get(
            "observation_id"
        )

        row_command = row.get(
            "command_id"
        )


        if (
            row_observation is not None
            and row_observation
            != observation_id
        ):

            raise ValueError(
                "Audit row observation_id linkage invalid."
            )


        if (
            row_command is not None
            and row_command
            != command_id
        ):

            raise ValueError(
                "Audit row command_id linkage invalid."
            )


    return {
        "observation":
            observation,

        "model_versions":
            model_versions,

        "images":
            images,

        "predictions":
            predictions,

        "sensor_readings":
            sensor_readings,

        "risk_scores":
            risk_scores,

        "forecasts":
            forecasts,

        "decision":
            decision,

        "command":
            command,

        "actions":
            actions,

        "sustainability_metrics":
            sustainability_metrics,

        "system_events":
            system_events,
    }


def _ensure_model_version(
    conn: sqlite3.Connection,
    row: Mapping[str, Any],
) -> None:

    existing = conn.execute(
        """
        SELECT
            model_version_id,
            model_name,
            model_sha256,
            artifact_path,
            created_at
        FROM model_versions
        WHERE model_version_id = ?
        """,
        (
            row[
                "model_version_id"
            ],
        ),
    ).fetchone()


    values = (
        row[
            "model_version_id"
        ],
        row[
            "model_name"
        ],
        row.get(
            "model_sha256"
        ),
        row.get(
            "artifact_path"
        ),
        row[
            "created_at"
        ],
    )


    if existing is None:

        conn.execute(
            """
            INSERT INTO model_versions (
                model_version_id,
                model_name,
                model_sha256,
                artifact_path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            values,
        )

        return


    if tuple(
        existing
    ) != values:

        raise ValueError(
            "Conflicting existing model_version_id."
        )


def write_audit_bundle(
    conn: sqlite3.Connection,
    bundle: Mapping[str, Any],
) -> dict[str, Any]:

    if not isinstance(
        conn,
        sqlite3.Connection,
    ):

        raise ValueError(
            "conn must be sqlite3.Connection."
        )


    original = deepcopy(
        bundle
    )


    normalized = _validate_bundle(
        bundle
    )


    conn.execute(
        "PRAGMA foreign_keys = ON"
    )


    conn.execute(
        "SAVEPOINT greenpulse_audit_bundle"
    )


    try:

        observation = normalized[
            "observation"
        ]


        conn.execute(
            """
            INSERT INTO observations (
                observation_id,
                timestamp,
                plant_id,
                crop
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                observation[
                    "observation_id"
                ],
                observation[
                    "timestamp"
                ],
                observation[
                    "plant_id"
                ],
                observation.get(
                    "crop"
                ),
            ),
        )


        for row in normalized[
            "model_versions"
        ]:

            _ensure_model_version(
                conn,
                row,
            )


        for row in normalized[
            "images"
        ]:

            conn.execute(
                """
                INSERT INTO images (
                    image_id,
                    observation_id,
                    image_path,
                    image_sha256,
                    captured_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row[
                        "image_id"
                    ],
                    row[
                        "observation_id"
                    ],
                    row[
                        "image_path"
                    ],
                    row.get(
                        "image_sha256"
                    ),
                    row.get(
                        "captured_at"
                    ),
                ),
            )


        for row in normalized[
            "predictions"
        ]:

            conn.execute(
                """
                INSERT INTO predictions (
                    prediction_id,
                    observation_id,
                    image_id,
                    model_version_id,
                    predicted_class,
                    confidence,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row[
                        "prediction_id"
                    ],
                    row[
                        "observation_id"
                    ],
                    row.get(
                        "image_id"
                    ),
                    row[
                        "model_version_id"
                    ],
                    row.get(
                        "predicted_class"
                    ),
                    row.get(
                        "confidence"
                    ),
                    row[
                        "created_at"
                    ],
                ),
            )


        for row in normalized[
            "sensor_readings"
        ]:

            conn.execute(
                """
                INSERT INTO sensor_readings (
                    sensor_reading_id,
                    observation_id,
                    sensor_id,
                    sensor_type,
                    value,
                    unit,
                    timestamp,
                    validation_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row[
                        "sensor_reading_id"
                    ],
                    row[
                        "observation_id"
                    ],
                    row[
                        "sensor_id"
                    ],
                    row.get(
                        "sensor_type"
                    ),
                    row.get(
                        "value"
                    ),
                    row.get(
                        "unit"
                    ),
                    row[
                        "timestamp"
                    ],
                    row.get(
                        "validation_status"
                    ),
                ),
            )


        for row in normalized[
            "risk_scores"
        ]:

            conn.execute(
                """
                INSERT INTO risk_scores (
                    risk_score_id,
                    observation_id,
                    model_version_id,
                    risk_score,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row[
                        "risk_score_id"
                    ],
                    row[
                        "observation_id"
                    ],
                    row[
                        "model_version_id"
                    ],
                    row[
                        "risk_score"
                    ],
                    row[
                        "created_at"
                    ],
                ),
            )


        for row in normalized[
            "forecasts"
        ]:

            conn.execute(
                """
                INSERT INTO forecasts (
                    forecast_id,
                    observation_id,
                    model_version_id,
                    forecast_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row[
                        "forecast_id"
                    ],
                    row[
                        "observation_id"
                    ],
                    row[
                        "model_version_id"
                    ],
                    row[
                        "forecast_json"
                    ],
                    row[
                        "created_at"
                    ],
                ),
            )


        decision = normalized[
            "decision"
        ]


        conn.execute(
            """
            INSERT INTO decisions (
                decision_id,
                observation_id,
                risk_score_id,
                forecast_id,
                decision,
                reason_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision[
                    "decision_id"
                ],
                decision[
                    "observation_id"
                ],
                decision[
                    "risk_score_id"
                ],
                decision[
                    "forecast_id"
                ],
                decision[
                    "decision"
                ],
                decision.get(
                    "reason_json"
                ),
                decision[
                    "created_at"
                ],
            ),
        )


        command = normalized[
            "command"
        ]


        conn.execute(
            """
            INSERT INTO commands (
                command_id,
                observation_id,
                decision_id,
                command_type,
                payload_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                command[
                    "command_id"
                ],
                command[
                    "observation_id"
                ],
                command[
                    "decision_id"
                ],
                command[
                    "command_type"
                ],
                command.get(
                    "payload_json"
                ),
                command[
                    "created_at"
                ],
            ),
        )


        for row in normalized[
            "actions"
        ]:

            conn.execute(
                """
                INSERT INTO actions (
                    action_id,
                    command_id,
                    action_state,
                    ack_type,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row[
                        "action_id"
                    ],
                    row[
                        "command_id"
                    ],
                    row[
                        "action_state"
                    ],
                    row.get(
                        "ack_type"
                    ),
                    row[
                        "created_at"
                    ],
                ),
            )


        for row in normalized[
            "sustainability_metrics"
        ]:

            conn.execute(
                """
                INSERT INTO sustainability_metrics (
                    metric_id,
                    observation_id,
                    command_id,
                    metric_name,
                    metric_value,
                    metric_unit,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row[
                        "metric_id"
                    ],
                    row.get(
                        "observation_id"
                    ),
                    row.get(
                        "command_id"
                    ),
                    row[
                        "metric_name"
                    ],
                    row.get(
                        "metric_value"
                    ),
                    row.get(
                        "metric_unit"
                    ),
                    row[
                        "created_at"
                    ],
                ),
            )


        for row in normalized[
            "system_events"
        ]:

            conn.execute(
                """
                INSERT INTO system_events (
                    event_id,
                    observation_id,
                    command_id,
                    event_type,
                    severity,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row[
                        "event_id"
                    ],
                    row.get(
                        "observation_id"
                    ),
                    row.get(
                        "command_id"
                    ),
                    row[
                        "event_type"
                    ],
                    row.get(
                        "severity"
                    ),
                    row.get(
                        "payload_json"
                    ),
                    row[
                        "created_at"
                    ],
                ),
            )


        conn.execute(
            "RELEASE SAVEPOINT greenpulse_audit_bundle"
        )


    except Exception:

        conn.execute(
            "ROLLBACK TO SAVEPOINT greenpulse_audit_bundle"
        )

        conn.execute(
            "RELEASE SAVEPOINT greenpulse_audit_bundle"
        )

        raise


    if bundle != original:

        raise RuntimeError(
            "Input audit bundle was mutated."
        )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "observation_id":
            normalized[
                "observation"
            ][
                "observation_id"
            ],

        "command_id":
            normalized[
                "command"
            ][
                "command_id"
            ],

        "written_counts": {
            "observations":
                1,

            "model_versions":
                len(
                    normalized[
                        "model_versions"
                    ]
                ),

            "images":
                len(
                    normalized[
                        "images"
                    ]
                ),

            "predictions":
                len(
                    normalized[
                        "predictions"
                    ]
                ),

            "sensor_readings":
                len(
                    normalized[
                        "sensor_readings"
                    ]
                ),

            "risk_scores":
                len(
                    normalized[
                        "risk_scores"
                    ]
                ),

            "forecasts":
                len(
                    normalized[
                        "forecasts"
                    ]
                ),

            "decisions":
                1,

            "commands":
                1,

            "actions":
                len(
                    normalized[
                        "actions"
                    ]
                ),

            "sustainability_metrics":
                len(
                    normalized[
                        "sustainability_metrics"
                    ]
                ),

            "system_events":
                len(
                    normalized[
                        "system_events"
                    ]
                ),
        },

        "atomic_write":
            True,

        "input_mutated":
            False,
    }
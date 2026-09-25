
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "greenpulse.db"


def get_recent_simulated_events(limit=20, db_path=None):
    """
    Read-only access to simulated hardware events.

    Does not execute commands or communicate
    with physical hardware.
    """

    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    db = (
        Path(db_path).resolve()
        if db_path is not None
        else DEFAULT_DB.resolve()
    )

    if not db.is_file():
        raise FileNotFoundError(
            "GreenPulse audit database not found."
        )

    # Open the database in SQLite read-only mode.
    connection = sqlite3.connect(
        db.as_uri() + "?mode=ro",
        uri=True,
        timeout=5
    )

    try:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute(
            """
            SELECT
                command_id,
                test_observation_id,
                plant_id,
                target,
                scenario,
                status,
                error_code,
                simulated,
                physical_actuation,
                logged_at_utc
            FROM simulated_actuator_events
            ORDER BY logged_at_utc DESC, command_id DESC
            LIMIT ?
            """,
            (limit,)
        )

        events = [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()

    for event in events:
        if (
            event["simulated"] != 1
            or event["physical_actuation"] != 0
            or not event["status"].startswith("SIMULATED_")
        ):
            raise ValueError(
                "Unexpected non-simulation audit record."
            )

        event["simulated"] = True
        event["physical_actuation"] = False

    return events

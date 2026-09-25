import json
import sqlite3
import hashlib
from pathlib import Path

DATABASE = Path("data/greenpulse.db")


def log_observation(response, image_bytes):

    DATABASE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    image_hash = hashlib.sha256(
        image_bytes
    ).hexdigest()

    with sqlite3.connect(DATABASE) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                observation_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                crop TEXT NOT NULL,
                image_sha256 TEXT NOT NULL,
                predicted_class TEXT,
                sensor_status TEXT,
                time_sync_status TEXT,
                decision TEXT NOT NULL,
                model_sha256 TEXT NOT NULL,
                response_json TEXT NOT NULL
            )
        """)

        conn.execute("""
            INSERT INTO observations VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            response["observation_id"],
            response["timestamp"],
            response["plant_id"],
            response["crop"],
            image_hash,
            response["vision"]["predicted_class"],
            response["sensor"]["status"],
            response["time_sync"]["status"],
            response["decision"]["action"],
            response["model"]["sha256"],
            json.dumps(response)
        ))

    return response["observation_id"]



def get_latest_observation():

    if not DATABASE.is_file():
        return None

    with sqlite3.connect(DATABASE) as conn:

        row = conn.execute("""
            SELECT response_json
            FROM observations
            ORDER BY rowid DESC
            LIMIT 1
        """).fetchone()

    if row is None:
        return None

    return json.loads(row[0])



def get_plant_history(plant_id, limit=10):

    if not DATABASE.is_file():
        return []

    with sqlite3.connect(DATABASE) as conn:
        rows = conn.execute("""
            SELECT response_json
            FROM observations
            WHERE plant_id = ?
            ORDER BY rowid DESC
            LIMIT ?
        """, (plant_id, limit)).fetchall()

    return [
        json.loads(row[0])
        for row in rows
    ]

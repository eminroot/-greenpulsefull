
import json
import sqlite3

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB = (
    ROOT / "data/active_learning_review.db"
)


@contextmanager
def connection(db_path):
    path = Path(db_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(path)

    try:
        yield conn
    finally:
        conn.close()


def initialize_review_queue(db_path=DEFAULT_DB):

    with connection(db_path) as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS review_queue (
                queue_key TEXT PRIMARY KEY,
                sample_id TEXT NOT NULL,
                crop TEXT NOT NULL,
                model_sha256 TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN (
                        'PENDING_REVIEW',
                        'REVIEWED'
                    )),
                payload_json TEXT NOT NULL
            )
            """
        )

        conn.commit()


def enqueue_review(
    queue_key,
    payload,
    db_path=DEFAULT_DB
):

    initialize_review_queue(db_path)

    encoded = json.dumps(
        payload,
        sort_keys=True,
        allow_nan=False
    )

    with connection(db_path) as conn:

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO review_queue (
                queue_key,
                sample_id,
                crop,
                model_sha256,
                created_at_utc,
                status,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, 'PENDING_REVIEW', ?)
            """,
            (
                queue_key,
                payload["sample_id"],
                payload["crop"],
                payload["model_sha256"],
                datetime.now(
                    timezone.utc
                ).isoformat(),
                encoded
            )
        )

        conn.commit()

        inserted = (
            cursor.rowcount == 1
        )

    return {
        "inserted": inserted,
        "queue_key": queue_key,
        "status": "PENDING_REVIEW"
    }


def list_pending_reviews(
    db_path=DEFAULT_DB
):

    initialize_review_queue(db_path)

    with connection(db_path) as conn:

        rows = conn.execute(
            """
            SELECT
                queue_key,
                payload_json
            FROM review_queue
            WHERE status = 'PENDING_REVIEW'
            ORDER BY created_at_utc ASC
            """
        ).fetchall()

    return [
        {
            "queue_key": queue_key,
            "payload": json.loads(
                payload_json
            )
        }
        for queue_key, payload_json
        in rows
    ]

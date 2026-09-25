"""
Upstream uploader.

Every result the Pi produces is written to a small SQLite queue on disk, then
pushed to your server by a background thread. The queue is the point: a
greenhouse Wi-Fi drop, a server restart or a flat internet connection must not
lose readings. Rows stay until the server accepts them.

A row the server refuses as malformed (400/413/422) will never succeed, so it
moves to a dead_letter table instead of sitting at the head of the queue and
blocking every reading behind it. Nothing is deleted silently.

Configured entirely by environment variables, see .env.example.
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import threading
import time
from contextlib import closing
from typing import Any

import requests

UPSTREAM_URL = os.environ.get("LEAFNODE_UPSTREAM_URL", "").strip()
UPSTREAM_TOKEN = os.environ.get("LEAFNODE_UPSTREAM_TOKEN", "").strip()
QUEUE_PATH = os.environ.get("LEAFNODE_QUEUE", "data/queue.db")
POLL_SECONDS = float(os.environ.get("LEAFNODE_UPSTREAM_POLL", "5"))
MAX_ATTEMPTS = int(os.environ.get("LEAFNODE_UPSTREAM_MAX_ATTEMPTS", "0"))  # 0 = forever
# Send the leaf photo with the reading, so the farmer sees what the camera saw.
SEND_IMAGES = os.environ.get("LEAFNODE_UPSTREAM_IMAGES", "1") == "1"

# The server said the record itself is wrong. Retrying cannot fix that.
# 401/403/404 are deliberately NOT here: a revoked token or a wrong URL is a
# configuration problem, and the readings are fine once it is corrected.
PERMANENT = {400, 413, 422}

_lock = threading.Lock()
# Set whenever a record is queued, so delivery starts at once instead of on the
# next poll. That is what makes a scan taken in the app feel immediate.
_wake = threading.Event()


def _connect():
    """Context manager that commits AND closes. sqlite3's own context
    manager commits but leaves the handle open, which leaks over weeks."""
    return closing(_open())


def _open() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(QUEUE_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(QUEUE_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_queue() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                payload     TEXT    NOT NULL,
                created_at  REAL    NOT NULL,
                attempts    INTEGER NOT NULL DEFAULT 0,
                last_error  TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dead_letter (
                id          INTEGER PRIMARY KEY,
                payload     TEXT    NOT NULL,
                created_at  REAL    NOT NULL,
                failed_at   REAL    NOT NULL,
                attempts    INTEGER NOT NULL,
                last_error  TEXT
            )
            """
        )
        conn.commit()


def enqueue(payload: dict[str, Any]) -> int:
    """Store a record for delivery. Returns the queue row id."""
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO outbox (payload, created_at) VALUES (?, ?)",
            (json.dumps(payload, allow_nan=False), time.time()),
        )
        conn.commit()
        row_id = int(cur.lastrowid)
    _wake.set()
    return row_id


def queue_depth() -> int:
    with _lock, _connect() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0])


def dead_letter_count() -> int:
    with _lock, _connect() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM dead_letter").fetchone()[0])


def _image_b64(payload: dict) -> str | None:
    """The stored frame, for the server to keep. Skipped for a phone scan: the
    server already holds the farmer's own photo of that leaf. A photo the camera
    took on request is new to the server, so it goes up like any other frame."""
    if not SEND_IMAGES:
        return None
    if payload.get("job_id") and payload.get("job_kind") != "camera":
        return None
    path = payload.get("image_path")
    if not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def _post(body: dict) -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if UPSTREAM_TOKEN:
        headers["Authorization"] = f"Bearer {UPSTREAM_TOKEN}"
    return requests.post(UPSTREAM_URL, json=body, headers=headers, timeout=30)


def _deliver(payload: dict) -> tuple[str, str]:
    """Returns (outcome, message). outcome is "ok", "retry" or "reject"."""
    try:
        image = _image_b64(payload)
    except OSError as exc:
        print(f"[upstream] could not read {payload.get('image_path')}: {exc}", flush=True)
        image = None

    try:
        resp = _post({**payload, "image_b64": image} if image else payload)
        if image and resp.status_code in (400, 413):
            # The photo was the problem, not the reading. Keep the reading.
            first = f"HTTP {resp.status_code}: {resp.text[:120]}"
            resp = _post(payload)
            if 200 <= resp.status_code < 300:
                return "ok", f"delivered without its image ({first})"
    except requests.RequestException as exc:
        return "retry", f"{type(exc).__name__}: {exc}"

    if 200 <= resp.status_code < 300:
        return "ok", ""
    message = f"HTTP {resp.status_code}: {resp.text[:200]}"
    if resp.status_code in PERMANENT:
        return "reject", message
    return "retry", message


def _bury(conn: sqlite3.Connection, row_id: int, attempts: int, err: str) -> None:
    conn.execute(
        """
        INSERT INTO dead_letter (id, payload, created_at, failed_at, attempts, last_error)
        SELECT id, payload, created_at, ?, ?, ? FROM outbox WHERE id = ?
        """,
        (time.time(), attempts, err, row_id),
    )
    conn.execute("DELETE FROM outbox WHERE id = ?", (row_id,))


def _worker() -> None:
    backoff = POLL_SECONDS
    while True:
        try:
            # Cleared before looking, so a record queued while we look still
            # wakes the wait below.
            _wake.clear()
            with _lock, _connect() as conn:
                row = conn.execute(
                    "SELECT id, payload, attempts FROM outbox ORDER BY id LIMIT 1"
                ).fetchone()

            if row is None:
                backoff = POLL_SECONDS
                _wake.wait(POLL_SECONDS)
                continue

            row_id, payload_json, attempts = row
            outcome, err = _deliver(json.loads(payload_json))
            attempts += 1

            with _lock, _connect() as conn:
                if outcome == "ok":
                    conn.execute("DELETE FROM outbox WHERE id = ?", (row_id,))
                    print(f"[upstream] delivered row {row_id}{' - ' + err if err else ''}", flush=True)
                elif outcome == "reject":
                    _bury(conn, row_id, attempts, err)
                    print(f"[upstream] server refused row {row_id}, moved to dead_letter: {err}", flush=True)
                elif MAX_ATTEMPTS and attempts >= MAX_ATTEMPTS:
                    _bury(conn, row_id, attempts, err)
                    print(f"[upstream] giving up on row {row_id} after {attempts} attempts, moved to dead_letter: {err}", flush=True)
                else:
                    conn.execute(
                        "UPDATE outbox SET attempts = ?, last_error = ? WHERE id = ?",
                        (attempts, err, row_id),
                    )
                    print(f"[upstream] row {row_id} failed (attempt {attempts}): {err}", flush=True)
                conn.commit()

            if outcome == "retry":
                backoff = min(backoff * 2, 300)   # cap at five minutes
                # A fresh record cuts the wait short: if the server is back,
                # there is no reason to sit out the rest of the backoff.
                _wake.wait(backoff)
            else:
                backoff = POLL_SECONDS

        except Exception as exc:   # the worker must never die
            print(f"[upstream] worker error: {exc}", flush=True)
            time.sleep(POLL_SECONDS)


def start_worker() -> bool:
    """Start delivery in the background. No-op when no upstream is configured."""
    init_queue()
    if not UPSTREAM_URL:
        print("[upstream] LEAFNODE_UPSTREAM_URL not set, results stay local only", flush=True)
        return False
    threading.Thread(target=_worker, name="leafnode-upstream", daemon=True).start()
    print(f"[upstream] worker started, target {UPSTREAM_URL}", flush=True)
    return True

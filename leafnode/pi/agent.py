"""
App request agent. Runs on the Pi next to the LeafNode service.

The node already pushes its own readings upstream (uploader.py does that). This
adds the other direction, for two things the farmer can ask for in the app:

  photo   they photographed a leaf with the phone. The photo waits on the
          server; this agent fetches it and hands it to the local LeafNode
          service exactly the way the ESP32 does, tagged with the job id.
  camera  they tapped "take a photo now". This agent asks the local service
          to have the ESP32 take one (POST /capture), tagged with the job id.

Either way the verdict then travels up through the same disk-backed outbox as
every other reading, so a dropped connection delays a result but never loses
it.

It dials out only, so the Pi needs no port forwarding and no static IP.

Reads the same .env as the service:
    LEAFNODE_UPSTREAM_URL     https://your-domain/api/v1/ingest/capture
    LEAFNODE_UPSTREAM_TOKEN   gp_...   (the device token from the app)
    LEAFNODE_NODE_KEY         the key the ESP32 also uses

    python agent.py
"""

from __future__ import annotations

import os
import sys
import time

import requests

INGEST_SUFFIX = "/api/v1/ingest/capture"

UPSTREAM = os.environ.get("LEAFNODE_UPSTREAM_URL", "").strip()
SERVER = os.environ.get("GREENPULSE_URL", "").strip().rstrip("/") or (
    UPSTREAM[: -len(INGEST_SUFFIX)] if UPSTREAM.endswith(INGEST_SUFFIX) else ""
)
TOKEN = (
    os.environ.get("GREENPULSE_TOKEN", "").strip()
    or os.environ.get("LEAFNODE_UPSTREAM_TOKEN", "").strip()
)
NODE_KEY = os.environ.get("LEAFNODE_NODE_KEY", "").strip()
PORT = os.environ.get("LEAFNODE_PORT", "8000")
ANALYZE = os.environ.get("LEAFNODE_ANALYZE", f"http://127.0.0.1:{PORT}/analyze")
CAPTURE = os.environ.get("LEAFNODE_CAPTURE", f"http://127.0.0.1:{PORT}/capture")
DEVICE_ID = os.environ.get("LEAFNODE_AGENT_DEVICE_ID", "phone-scan")
POLL_WAIT = int(os.environ.get("GREENPULSE_POLL_WAIT", "25"))
# What this agent can do. The server only hands out jobs listed here.
KINDS = "photo,camera"

HEADERS = {"Authorization": f"Bearer {TOKEN}"}
# Kept alive between polls, so claiming a job does not start with a new TLS
# handshake to the server.
SERVER_SESSION = requests.Session()


def log(message: str) -> None:
    print(f"[agent] {message}", flush=True)


def claim_job() -> dict | None:
    """Long polls for work. Returns None when there is nothing to do."""
    res = SERVER_SESSION.get(
        f"{SERVER}/api/v1/ingest/jobs",
        params={"wait": POLL_WAIT, "kinds": KINDS},
        headers=HEADERS,
        timeout=POLL_WAIT + 15,
    )
    if res.status_code == 204:
        return None
    res.raise_for_status()
    return res.json()


def fetch_photo(job: dict) -> bytes:
    res = SERVER_SESSION.get(f"{SERVER}{job['image_url']}", headers=HEADERS, timeout=30)
    res.raise_for_status()
    return res.content


def score_locally(job: dict, photo: bytes) -> dict:
    """Hands the frame to the LeafNode service, same as the ESP32 does. The
    service queues the verdict with the job id and delivers it at once."""
    res = requests.post(
        ANALYZE,
        files={"image": ("leaf.jpg", photo, "image/jpeg")},
        data={"device_id": DEVICE_ID, "job_id": job["job_id"]},
        headers={"X-Node-Key": NODE_KEY},
        timeout=120,
    )
    res.raise_for_status()
    return res.json()


class CameraFailed(Exception):
    """The camera could not produce a photo. The message is the code the app
    turns into words: camera_unreachable, camera_refused, camera_outdated,
    camera_failed."""


def take_photo(job: dict) -> dict:
    """Has the LeafNode service get a photo from the ESP32 now and score it.
    The service queues the verdict, photo included, with the job id."""
    try:
        res = requests.post(
            CAPTURE,
            params={"job_id": job["job_id"]},
            headers={"X-Node-Key": NODE_KEY},
            # The service gives the camera up to 40 s, retries included.
            timeout=75,
        )
    except requests.RequestException as exc:
        raise CameraFailed("camera_failed") from exc
    if res.status_code in (502, 504):
        try:
            body = res.json()
        except ValueError:
            body = {}
        log(f"camera: {body.get('why') or res.text[:200]}")
        raise CameraFailed(str(body.get("detail") or "camera_failed")[:60])
    res.raise_for_status()
    return res.json()


def fail(job: dict, error: str) -> None:
    """Tell the server so the farmer sees a real failure instead of waiting."""
    try:
        SERVER_SESSION.post(
            f"{SERVER}/api/v1/ingest/jobs/fail",
            json={"job_id": job["job_id"], "error": error[:500]},
            headers=HEADERS,
            timeout=15,
        )
    except requests.RequestException as exc:
        log(f"could not report failure: {exc}")


def main() -> int:
    if not SERVER or not TOKEN:
        print(
            "Set LEAFNODE_UPSTREAM_URL (ending in /api/v1/ingest/capture) and "
            "LEAFNODE_UPSTREAM_TOKEN in .env first.",
            file=sys.stderr,
        )
        return 2
    if not NODE_KEY:
        print("Set LEAFNODE_NODE_KEY in .env first (setup.sh generates one).", file=sys.stderr)
        return 2

    log(f"watching {SERVER} for scans, scoring via {ANALYZE}")
    backoff = 2

    while True:
        try:
            job = claim_job()
            backoff = 2
            if job is None:
                continue

            kind = job.get("kind") or "photo"
            log(f"claimed {kind} job {job['job_id']}")
            try:
                if kind == "camera":
                    verdict = take_photo(job)
                else:
                    verdict = score_locally(job, fetch_photo(job))
            except CameraFailed as exc:
                log(f"job {job['job_id']}: the camera took no photo ({exc})")
                fail(job, str(exc))
                continue
            except requests.RequestException as exc:
                log(f"scoring failed: {exc}")
                fail(job, str(exc))
                continue

            if verdict.get("unreadable"):
                # Nothing was queued for this one. The code after the colon is
                # what the app turns into "too dark, retake it" and the like.
                log(f"job {job['job_id']} photo unreadable: {verdict['unreadable']}")
                fail(job, f"unreadable:{verdict['unreadable']}")
                continue

            log(
                f"job {job['job_id']} scored {verdict.get('risk_level')} "
                f"({verdict.get('risk_score')}), queued for delivery"
            )

        except requests.RequestException as exc:
            # Server restart, flaky greenhouse wifi. Back off and keep going.
            log(f"upstream problem: {exc}; retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
        except KeyboardInterrupt:
            log("stopping")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The farmer asks the greenhouse camera for a photo now, off schedule.

App -> server queues a camera job -> the Pi's agent claims it, has the ESP32
take the photo, scores it -> the verdict and the photo come back through the
normal ingest path and close the job.
"""

from __future__ import annotations

import base64

from app.config import settings
from tests.test_flow import TINY_JPEG, _capture_body

CAMERA_KINDS = {"kinds": "photo,camera", "wait": 2}


def _request(client, grower, auth):
    res = client.post(f"/api/v1/sites/{grower['site']['id']}/camera/capture", headers=auth)
    assert res.status_code == 202, res.text
    return res.json()


def _drain(client, node):
    """Claims and fails whatever a test left open, so the next test starts
    with an empty queue."""
    while True:
        res = client.get("/api/v1/ingest/jobs", params={**CAMERA_KINDS, "wait": 0},
                         headers=node["headers"])
        if res.status_code == 204:
            return
        client.post("/api/v1/ingest/jobs/fail",
                    json={"job_id": res.json()["job_id"], "error": "test cleanup"},
                    headers=node["headers"])


def test_camera_request_is_taken_and_scored_by_the_node(client, node, grower, auth):
    _drain(client, node)
    submitted = _request(client, grower, auth)
    assert submitted["kind"] == "camera"
    job_id = submitted["job_id"]

    claimed = client.get("/api/v1/ingest/jobs", params=CAMERA_KINDS, headers=node["headers"])
    assert claimed.status_code == 200, claimed.text
    job = claimed.json()
    assert job["job_id"] == job_id
    assert job["kind"] == "camera"
    # nothing to download: the photo does not exist until the camera takes it
    assert job["image_url"] is None

    # the Pi reports the camera's frame, photo included, tagged with the job
    done = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body(
            "cam-001",
            job_id=job_id,
            risk_score=37.0,
            risk_level="medium",
            image_b64=base64.b64encode(TINY_JPEG).decode(),
        ),
        headers=node["headers"],
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "stored"

    status = client.get(f"/api/v1/scans/{job_id}", headers=auth).json()
    assert status["kind"] == "camera"
    assert status["status"] == "done"
    capture = status["capture"]
    # the greenhouse camera took it, so it is the node's frame, not the phone's
    assert capture["source"] == "node"
    assert capture["risk_score"] == 37.0

    img = client.get(capture["image_url"], headers=auth)
    assert img.status_code == 200 and img.content == TINY_JPEG

    live = client.get(f"/api/v1/sites/{grower['site']['id']}/live", headers=auth).json()
    assert live["capture"]["id"] == capture["id"]


def test_an_agent_that_cannot_take_photos_is_not_handed_one(client, node, grower, auth):
    """An agent from before camera requests polls without `kinds`. It must get
    204, not a job whose image_url is null and which it would fail."""
    _drain(client, node)
    job_id = _request(client, grower, auth)["job_id"]

    old_agent = client.get("/api/v1/ingest/jobs", params={"wait": 1}, headers=node["headers"])
    assert old_agent.status_code == 204

    status = client.get(f"/api/v1/scans/{job_id}", headers=auth).json()
    assert status["status"] == "pending"
    _drain(client, node)


def test_a_second_tap_is_the_same_request(client, node, grower, auth):
    _drain(client, node)
    first = _request(client, grower, auth)
    second = _request(client, grower, auth)
    assert second["job_id"] == first["job_id"]

    # still one photo once the node has it
    claimed = client.get("/api/v1/ingest/jobs", params=CAMERA_KINDS, headers=node["headers"])
    assert claimed.json()["job_id"] == first["job_id"]
    third = _request(client, grower, auth)
    assert third["job_id"] == first["job_id"]
    assert third["status"] == "claimed"
    _drain(client, node)
    client.post("/api/v1/ingest/jobs/fail",
                json={"job_id": first["job_id"], "error": "test cleanup"},
                headers=node["headers"])


def test_camera_failure_reason_reaches_the_app(client, node, grower, auth):
    _drain(client, node)
    job_id = _request(client, grower, auth)["job_id"]
    client.get("/api/v1/ingest/jobs", params=CAMERA_KINDS, headers=node["headers"])

    res = client.post(
        "/api/v1/ingest/jobs/fail",
        json={"job_id": job_id, "error": "unreadable:too_dark"},
        headers=node["headers"],
    )
    assert res.status_code == 204

    status = client.get(f"/api/v1/scans/{job_id}", headers=auth).json()
    assert status["status"] == "failed"
    assert status["error"] == "unreadable:too_dark"
    # a new request after a failure is a new photo, not the failed job again
    assert _request(client, grower, auth)["job_id"] != job_id
    _drain(client, node)


def test_a_request_no_node_takes_expires_when_the_app_asks(client, node, grower, auth, monkeypatch):
    """With the Pi switched off nothing ever polls, so the status read itself
    has to notice the job is past its time."""
    _drain(client, node)
    job_id = _request(client, grower, auth)["job_id"]
    # Below zero, so "older than the timeout" holds even inside one clock tick.
    monkeypatch.setattr(settings, "scan_job_timeout_seconds", -1)

    status = client.get(f"/api/v1/scans/{job_id}", headers=auth).json()
    assert status["status"] == "expired"


def test_camera_request_needs_the_greenhouse_owner(client, grower):
    other = client.post(
        "/api/v1/auth/register",
        json={"email": "camera-stranger@example.com", "password": "greenhouse1"},
    ).json()
    res = client.post(
        f"/api/v1/sites/{grower['site']['id']}/camera/capture",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert res.status_code == 404
    assert client.post(f"/api/v1/sites/{grower['site']['id']}/camera/capture").status_code == 401


def test_a_waiting_node_is_woken_the_moment_a_photo_is_asked_for(client, node, grower, auth):
    """The Pi sits in the long poll. Queueing a request must reach it now, not
    on the poll's next look at the database a few seconds later."""
    import threading
    import time

    _drain(client, node)
    result: dict = {}

    def pi_waiting() -> None:
        started = time.monotonic()
        res = client.get("/api/v1/ingest/jobs", params={"kinds": "photo,camera", "wait": 15},
                         headers=node["headers"])
        result["status"] = res.status_code
        result["job"] = res.json() if res.status_code == 200 else None
        result["claimed_at"] = time.monotonic()
        result["started"] = started

    waiting = threading.Thread(target=pi_waiting)
    waiting.start()
    time.sleep(0.6)  # the poll has looked, found nothing, and is waiting
    asked_at = time.monotonic()
    job_id = _request(client, grower, auth)["job_id"]
    waiting.join(timeout=20)

    assert result["status"] == 200 and result["job"]["job_id"] == job_id
    # The safety net would take up to 5 s; being woken takes a blink.
    assert result["claimed_at"] - asked_at < 1.5, result["claimed_at"] - asked_at
    client.post("/api/v1/ingest/jobs/fail", json={"job_id": job_id, "error": "test cleanup"},
                headers=node["headers"])

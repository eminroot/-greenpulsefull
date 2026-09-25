"""The path a real reading takes, end to end.

Pi uploads a scored leaf -> server fuses it with the greenhouse sensors ->
the phone reads it back and is pushed the next one live.
"""

from __future__ import annotations

import base64
import json



# A 1x1 JPEG, enough to exercise the image path without a fixture file.
TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
    "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="
)


def _capture_body(capture_id: str, **overrides) -> dict:
    """The record shape pi/uploader.py sends, unchanged."""
    body = {
        "capture_id": capture_id,
        "site_id": "site-01",
        "device_id": "leafnode-01",
        "received_at": "2026-09-23T09:00:00+00:00",
        "latency_ms": 184.2,
        "image_bytes": 45231,
        "image_width": 800,
        "image_height": 600,
        "image_path": "data/captures/x.jpg",
        "sensors": {"temperature": 24.5, "humidity": 61.0, "soil_moisture": 58.0},
        "risk_score": 18.0,
        "risk_level": "low",
        "label": "healthy",
        "confidence": 0.91,
        "model_version": "leafnode-placeholder-1",
        "extra": {"green_ratio": 0.82},
    }
    body.update(overrides)
    return body


# --- accounts --------------------------------------------------------------


def test_register_rejects_weak_password(client):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "1234567"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "password_too_short"

    res = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "12345678"},
    )
    assert res.json()["detail"] == "password_needs_letter"


def test_duplicate_email_is_rejected(client, grower):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "GROWER@example.com", "password": "greenhouse1"},
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "email_in_use"


def test_login_and_wrong_password(client):
    ok = client.post(
        "/api/v1/auth/login",
        json={"email": "grower@example.com", "password": "greenhouse1"},
    )
    assert ok.status_code == 200
    assert ok.json()["user"]["display_name"] == "Test Grower"

    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "grower@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401
    assert bad.json()["detail"] == "invalid_credentials"


def test_me_requires_a_token(client, auth):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth).json()["email"] == "grower@example.com"


def test_refresh_rotates_and_old_token_dies(client, grower):
    first = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": grower["refresh"]}
    )
    assert first.status_code == 200
    rotated = first.json()["refresh_token"]
    assert rotated != grower["refresh"]

    replay = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": grower["refresh"]}
    )
    assert replay.status_code == 401

    grower["refresh"] = rotated


# --- device pairing --------------------------------------------------------


def test_node_token_authenticates(client, node):
    res = client.get("/api/v1/ingest/health", headers=node["headers"])
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_unknown_node_token_is_refused(client):
    res = client.get(
        "/api/v1/ingest/health", headers={"Authorization": "Bearer gp_not-a-real-token"}
    )
    assert res.status_code == 401


def test_grower_cannot_read_another_growers_site(client, grower):
    other = client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "greenhouse1"},
    ).json()
    res = client.get(
        f"/api/v1/sites/{grower['site']['id']}/live",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert res.status_code == 404


# --- the reading path ------------------------------------------------------


def test_node_upload_is_fused_and_stored(client, node, grower, auth):
    res = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("cap-001"),
        headers=node["headers"],
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "stored"

    # soil 58 and temp 24.5 both sit inside the ideal bands, so the only stress
    # is the model score: 18 * 0.4 renormalised over damage+water+thermal.
    assert body["gpss_score"] == 8
    assert body["risk_level"] == "Low"
    assert body["decision"] == "MONITORING"

    live = client.get(f"/api/v1/sites/{grower['site']['id']}/live", headers=auth).json()
    assert live["capture"]["risk_score"] == 18.0
    assert live["capture"]["label"] == "healthy"
    assert live["reading"]["temperature"] == 24.5
    assert live["reading"]["soil_moisture"] == 58.0
    # No light probe is wired, so it reports as absent rather than as a number.
    assert live["reading"]["light"] is None
    assert live["capture"]["signals"]["light"] is False
    assert live["capture"]["signals"]["water"] is True


def test_redelivery_does_not_duplicate(client, node, grower, auth):
    again = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("cap-001"),
        headers=node["headers"],
    )
    assert again.status_code == 200
    assert again.json()["status"] == "duplicate"

    captures = client.get(
        f"/api/v1/sites/{grower['site']['id']}/captures", headers=auth
    ).json()
    assert len([c for c in captures if c["node_capture_id"] == "cap-001"]) == 1


def test_dry_soil_triggers_irrigation(client, node, grower, auth):
    res = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body(
            "cap-002",
            risk_score=45.0,
            risk_level="medium",
            sensors={"temperature": 23.0, "humidity": 55.0, "soil_moisture": 5.0},
        ),
        headers=node["headers"],
    )
    body = res.json()
    assert body["gpss_score"] == 53
    assert body["stress_type"] == "Water Stress"
    assert body["decision"] == "IRRIGATION_ON"
    assert body["actuator"] == "WATER_PUMP"


def test_heat_triggers_ventilation(client, node):
    res = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body(
            "cap-003",
            risk_score=37.0,
            sensors={"temperature": 46.0, "humidity": 30.0, "soil_moisture": 24.7},
        ),
        headers=node["headers"],
    )
    body = res.json()
    assert body["stress_type"] == "Heat Stress"
    assert body["decision"] == "VENTILATION_ON"


def test_moderate_heat_alone_stays_in_monitoring(client, node):
    """Documents how the scoring weights actually behave.

    Temperature carries 0.15 of the score while autonomous action starts at 50,
    so a hot but otherwise healthy canopy is watched rather than vented. This is
    the behaviour of the reference engine, kept deliberately; the test is here
    so a future change to the weights is a visible decision and not a surprise.
    """
    res = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body(
            "cap-003b",
            risk_score=20.0,
            sensors={"temperature": 42.0, "humidity": 30.0, "soil_moisture": 60.0},
        ),
        headers=node["headers"],
    )
    body = res.json()
    assert body["stress_type"] == "Heat Stress"
    assert body["gpss_score"] == 24
    assert body["decision"] == "MONITORING"


def test_missing_sensors_still_score(client, node):
    """A node whose probes are not wired yet still produces a usable verdict
    from the model score alone."""
    res = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("cap-004", risk_score=80.0, risk_level="critical", sensors=None),
        headers=node["headers"],
    )
    body = res.json()
    assert body["gpss_score"] == 80
    assert body["decision"] == "ALERT_AGRONOMIST"
    assert body["notify_farmer"] is True


def test_image_upload_and_readback(client, node, grower, auth):
    client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("cap-005"),
        headers=node["headers"],
    )
    up = client.post(
        "/api/v1/ingest/capture/cap-005/image",
        files={"image": ("leaf.jpg", TINY_JPEG, "image/jpeg")},
        headers=node["headers"],
    )
    assert up.status_code == 204, up.text

    captures = client.get(
        f"/api/v1/sites/{grower['site']['id']}/captures", headers=auth
    ).json()
    target = next(c for c in captures if c["node_capture_id"] == "cap-005")
    assert target["image_url"]

    img = client.get(target["image_url"], headers=auth)
    assert img.status_code == 200
    assert img.content == TINY_JPEG

    # and not to somebody else
    assert client.get(target["image_url"]).status_code == 401


# --- what the app renders --------------------------------------------------


def test_series_and_sustainability_come_from_real_rows(client, grower, auth):
    site_id = grower["site"]["id"]

    series = client.get(
        f"/api/v1/sites/{site_id}/series",
        params={"metric": "soil_moisture", "hours": 720},
        headers=auth,
    ).json()
    assert [p["v"] for p in series["points"]]

    bad = client.get(
        f"/api/v1/sites/{site_id}/series", params={"metric": "nonsense"}, headers=auth
    )
    assert bad.status_code == 400

    sus = client.get(f"/api/v1/sites/{site_id}/sustainability", headers=auth).json()
    assert sus["irrigation_events"] == 1  # exactly the one dry soil reading
    assert sus["ventilation_events"] == 1
    assert sus["alerts"] == 1
    assert sus["autonomous_actions"] == 2


def test_live_is_empty_before_any_node_reports(client):
    fresh = client.post(
        "/api/v1/auth/register",
        json={"email": "fresh@example.com", "password": "greenhouse1"},
    ).json()
    headers = {"Authorization": f"Bearer {fresh['access_token']}"}
    site = client.get("/api/v1/sites", headers=headers).json()[0]

    live = client.get(f"/api/v1/sites/{site['id']}/live", headers=headers).json()
    assert live["capture"] is None
    assert live["reading"] is None
    assert live["online"] is False


# --- phone submitted scan --------------------------------------------------


def test_phone_scan_is_scored_by_the_node(client, node, grower, auth):
    site_id = grower["site"]["id"]

    submitted = client.post(
        f"/api/v1/sites/{site_id}/scans",
        files={"image": ("leaf.jpg", TINY_JPEG, "image/jpeg")},
        headers=auth,
    )
    assert submitted.status_code == 202, submitted.text
    job_id = submitted.json()["job_id"]

    # the node picks the job up
    claimed = client.get(
        "/api/v1/ingest/jobs", params={"wait": 2}, headers=node["headers"]
    )
    assert claimed.status_code == 200, claimed.text
    job = claimed.json()
    assert job["job_id"] == job_id

    # ... downloads the photo the farmer took ...
    img = client.get(job["image_url"], headers=node["headers"])
    assert img.status_code == 200
    assert img.content == TINY_JPEG

    # ... and reports the verdict back through the normal ingest path
    done = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("scan-001", job_id=job_id, risk_score=44.0, risk_level="medium"),
        headers=node["headers"],
    )
    assert done.status_code == 200

    status = client.get(f"/api/v1/scans/{job_id}", headers=auth).json()
    assert status["status"] == "done"
    assert status["capture"]["source"] == "phone"
    assert status["capture"]["risk_score"] == 44.0


def test_node_polling_returns_204_when_idle(client, node):
    res = client.get("/api/v1/ingest/jobs", params={"wait": 1}, headers=node["headers"])
    assert res.status_code == 204


def test_redelivered_scan_answer_still_closes_the_job(client, node, grower, auth):
    """The Pi can deliver one verdict twice. If the copy that lands first does
    not close the scan, the copy that does must not be dropped as a plain
    duplicate, or the farmer is told no node answered."""
    site_id = grower["site"]["id"]
    job_id = client.post(
        f"/api/v1/sites/{site_id}/scans",
        files={"image": ("leaf.jpg", TINY_JPEG, "image/jpeg")},
        headers=auth,
    ).json()["job_id"]
    client.get("/api/v1/ingest/jobs", params={"wait": 2}, headers=node["headers"])

    first = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("scan-race", sensors=None, risk_score=61.0, risk_level="high"),
        headers=node["headers"],
    )
    assert first.json()["status"] == "stored"
    assert client.get(f"/api/v1/scans/{job_id}", headers=auth).json()["status"] == "claimed"

    again = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("scan-race", sensors=None, job_id=job_id, risk_score=61.0),
        headers=node["headers"],
    )
    assert again.json()["status"] == "duplicate"

    status = client.get(f"/api/v1/scans/{job_id}", headers=auth).json()
    assert status["status"] == "done"
    assert status["capture"]["source"] == "phone"
    assert status["capture"]["risk_score"] == 61.0
    # the farmer's own photo is handed to the capture, not left orphaned
    img = client.get(status["capture"]["image_url"], headers=auth)
    assert img.status_code == 200 and img.content == TINY_JPEG


def test_reading_from_a_pi_with_a_wrong_clock_is_filed_at_arrival(client, node, grower, auth):
    res = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("cap-future", received_at="2031-01-01T00:00:00+00:00"),
        headers=node["headers"],
    )
    assert res.status_code == 200, res.text
    captures = client.get(
        f"/api/v1/sites/{grower['site']['id']}/captures", headers=auth
    ).json()
    target = next(c for c in captures if c["node_capture_id"] == "cap-future")
    assert target["captured_at"] < "2030"


def test_overlong_device_id_is_refused_not_a_500(client, node):
    res = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("cap-longid", device_id="x" * 200),
        headers=node["headers"],
    )
    assert res.status_code == 422


# --- live push -------------------------------------------------------------


def test_new_reading_is_pushed_to_an_open_dashboard(client, node, grower):
    site_id = grower["site"]["id"]
    received: list[dict] = []

    ticket = client.post(
        f"/api/v1/sites/{site_id}/stream/ticket",
        headers={"Authorization": f"Bearer {grower['access']}"},
    ).json()["ticket"]

    with client.websocket_connect(
        f"/api/v1/sites/{site_id}/stream?ticket={ticket}"
    ) as ws:
        # "ready" confirms this dashboard is subscribed before anything uploads.
        assert ws.receive_json()["type"] == "ready"

        upload = client.post(
            "/api/v1/ingest/capture",
            json=_capture_body("cap-live", risk_score=55.0, risk_level="high"),
            headers=node["headers"],
        )
        assert upload.status_code == 200

        for _ in range(5):
            message = ws.receive_json()
            if message["type"] == "capture":
                received.append(message)
                break

    assert received, "the dashboard should have been pushed the new reading"
    assert received[0]["capture"]["node_capture_id"] == "cap-live"
    assert received[0]["capture"]["risk_score"] == 55.0


def test_stream_rejects_a_bad_ticket(client, grower):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/api/v1/sites/{grower['site']['id']}/stream?ticket=nope"
        ) as ws:
            ws.receive_json()


def test_an_access_token_is_not_a_stream_ticket(client, grower):
    """The token must not work in the URL any more: that is the whole point of
    the ticket, since the URL reaches the proxy's access log."""
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/api/v1/sites/{grower['site']['id']}/stream?ticket={grower['access']}"
        ) as ws:
            ws.receive_json()


# --- account removal -------------------------------------------------------


def test_delete_account_removes_everything(client):
    made = client.post(
        "/api/v1/auth/register",
        json={"email": "leaving@example.com", "password": "greenhouse1"},
    ).json()
    headers = {"Authorization": f"Bearer {made['access_token']}"}

    assert client.delete("/api/v1/auth/me", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "leaving@example.com", "password": "greenhouse1"},
        ).status_code
        == 401
    )


def test_clearing_history_keeps_the_action_record(client, node, grower, auth):
    """Readings and their photos go; the actuator events stay.

    Those events are what the system actually did, and the savings figures are
    counted from them, so clearing the photo history must not rewrite history.
    """
    site_id = grower["site"]["id"]

    # Stand on its own rather than on whatever earlier tests happened to store.
    acted = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body(
            "cap-clear",
            risk_score=45.0,
            sensors={"temperature": 23.0, "humidity": 55.0, "soil_moisture": 5.0},
        ),
        headers=node["headers"],
    ).json()
    assert acted["decision"] == "IRRIGATION_ON"

    before = client.get(f"/api/v1/sites/{site_id}/sustainability", headers=auth).json()
    assert before["autonomous_actions"] > 0

    assert client.delete(f"/api/v1/sites/{site_id}/captures", headers=auth).status_code == 204
    assert client.get(f"/api/v1/sites/{site_id}/captures", headers=auth).json() == []

    after = client.get(f"/api/v1/sites/{site_id}/sustainability", headers=auth).json()
    assert after["autonomous_actions"] == before["autonomous_actions"]
    assert after["irrigation_events"] == before["irrigation_events"]


def test_score_preview_matches_the_real_engine(client, node, grower, auth):
    """The panel's twin must predict what the greenhouse would actually do.

    Same inputs through the preview endpoint and through a real node upload have
    to produce the same verdict, or the twin is lying to the operator.
    """
    sensors = {"temperature": 23.0, "humidity": 55.0, "soil_moisture": 5.0}

    preview = client.post(
        "/api/v1/score/preview",
        json={"damage_percentage": 45.0, **sensors},
        headers=auth,
    )
    assert preview.status_code == 200, preview.text
    p = preview.json()

    real = client.post(
        "/api/v1/ingest/capture",
        json=_capture_body("cap-preview", risk_score=45.0, sensors=sensors),
        headers=node["headers"],
    ).json()

    assert p["gpss_score"] == real["gpss_score"]
    assert p["risk_level"] == real["risk_level"]
    assert p["stress_type"] == real["stress_type"]
    assert p["decision"] == real["decision"]
    assert p["actuator"] == real["actuator"]


def test_score_preview_stores_nothing(client, grower, auth):
    site_id = grower["site"]["id"]
    before = client.get(f"/api/v1/sites/{site_id}/captures", headers=auth).json()

    client.post(
        "/api/v1/score/preview",
        json={"damage_percentage": 90.0, "soil_moisture": 2.0, "temperature": 44.0},
        headers=auth,
    )

    after = client.get(f"/api/v1/sites/{site_id}/captures", headers=auth).json()
    assert len(after) == len(before)


def test_score_preview_needs_a_signed_in_grower(client):
    assert client.post("/api/v1/score/preview", json={"damage_percentage": 10}).status_code == 401

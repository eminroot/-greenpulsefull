"""The trained leaf model's verdict, from the Pi's record to the phone.

The node sends its diagnosis in extra.diagnosis (leafnode/pi/leaf_classifier.py).
These pin what the server does with it: expose it to both clients, let a sure
disease reach the farmer even when every sensor reads perfect, keep an
unsure one quiet, and keep scoring from the sensors when a photo is too dark to
read instead of calling the leaf healthy.

Runs in its own greenhouse so the counts test_flow.py asserts stay untouched.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.engine.decision import decide
from app.engine.diagnosis import MIN_CONFIDENCE, parse_diagnosis
from app.engine.gpss import NothingToScore, compute_gpss

IDEAL = {"temperature": 23.0, "humidity": 60.0, "soil_moisture": 58.0, "light": 600.0}


def _diagnosis(code: str, confidence: float, crop: str = "tomato", top=None) -> dict:
    return {
        "status": "ok",
        "crop": crop,
        "code": code,
        "healthy": code == "healthy",
        "confidence": confidence,
        "top": top if top is not None else [{"code": code, "p": confidence}],
        "model": "tomato_clean_v1",
        "network_ms": 3.1,
        "quality": {"brightness": 120.0, "leaf_share": 0.4},
    }


def _unreadable(reason: str = "too_dark") -> dict:
    return {"status": "unreadable", "reason": reason, "crop": "tomato", "model": "tomato_clean_v1",
            "quality": {"brightness": 4.2, "leaf_share": 0.0}}


def _body(capture_id: str, *, at: datetime, diagnosis: dict, sensors=IDEAL, score=None, **extra) -> dict:
    ok = diagnosis["status"] == "ok"
    return {
        "capture_id": capture_id,
        "device_id": "leafnode-01",
        "received_at": at.isoformat(),
        "sensors": sensors,
        "risk_score": score if ok else None,
        "risk_level": ("critical" if (score or 0) >= 75 else "low") if ok else None,
        "label": diagnosis.get("code") or diagnosis.get("reason"),
        "confidence": diagnosis.get("confidence"),
        "model_version": "tomato_clean_v1",
        "extra": {"diagnosis": diagnosis},
        **extra,
    }


@pytest.fixture(scope="module")
def site(client, auth) -> dict:
    res = client.post("/api/v1/sites", json={"name": "Tomato house", "crop": "tomato"}, headers=auth)
    assert res.status_code == 201, res.text
    site = res.json()
    paired = client.post(
        f"/api/v1/sites/{site['id']}/devices", json={"name": "Pi", "kind": "pi"}, headers=auth
    ).json()
    return {"id": site["id"], "node": {"Authorization": f"Bearer {paired['token']}"}}


# --- parsing ------------------------------------------------------------------


def test_parse_reads_a_full_verdict():
    d = parse_diagnosis({"diagnosis": _diagnosis(
        "late_blight", 0.97,
        top=[{"code": "late_blight", "p": 0.97}, {"code": "early_blight", "p": 0.02}],
    )})
    assert d.status == "ok" and d.code == "late_blight" and d.confidence == 0.97
    assert d.healthy is False and d.disease_found and not d.uncertain
    # The top class is the finding, not an alternative to itself.
    assert d.alternatives == [{"code": "early_blight", "p": 0.02}]


def test_parse_decides_healthy_from_the_code_not_the_flag():
    raw = _diagnosis("late_blight", 0.9)
    raw["healthy"] = True
    assert parse_diagnosis({"diagnosis": raw}).healthy is False


@pytest.mark.parametrize(
    "broken",
    [
        {"status": "ok", "code": "late_blight", "confidence": 1.7},
        {"status": "ok", "code": "late_blight", "confidence": True},
        {"status": "ok", "code": "Late Blight!", "confidence": 0.9},
        {"status": "ok", "confidence": 0.9},
        {"status": "maybe", "code": "late_blight", "confidence": 0.9},
        "late_blight",
    ],
)
def test_parse_drops_a_malformed_verdict(broken):
    assert parse_diagnosis({"diagnosis": broken}) is None


def test_records_without_a_diagnosis_have_none():
    assert parse_diagnosis(None) is None
    assert parse_diagnosis({"green_ratio": 0.8}) is None


# --- engine -------------------------------------------------------------------


def test_sure_disease_alerts_even_with_perfect_sensors():
    """The leaf is 40% of the score: a certain late blight in an otherwise
    perfect greenhouse scores 38, below the action threshold."""
    gpss = compute_gpss(damage_percentage=95, **{k: IDEAL[k] for k in ("soil_moisture", "temperature", "light")})
    assert gpss.gpss_score == 38
    assert decide(gpss.gpss_score, gpss.stress_type).decision == "MONITORING"

    d = parse_diagnosis({"diagnosis": _diagnosis("late_blight", 0.97)})
    decision = decide(gpss.gpss_score, gpss.stress_type, d)
    assert decision.decision == "ALERT_AGRONOMIST"
    assert decision.actuator == "NONE"
    assert decision.notify_farmer is True
    assert "late_blight" in decision.reason


def test_unsure_disease_does_not_alert():
    d = parse_diagnosis({"diagnosis": _diagnosis("leaf_mold", MIN_CONFIDENCE - 0.01)})
    assert d.uncertain and not d.disease_found
    assert decide(20, "Tissue Damage", d).decision == "MONITORING"


def test_healthy_leaf_does_not_alert():
    d = parse_diagnosis({"diagnosis": _diagnosis("healthy", 0.99)})
    assert decide(3, "Healthy", d).decision == "MONITORING"


def test_disease_never_switches_an_actuator_but_rides_along_with_one():
    """Dry soil still waters; the farmer also hears about the leaf."""
    d = parse_diagnosis({"diagnosis": _diagnosis("bacterial_spot", 0.9)})
    decision = decide(62, "Water Stress", d)
    assert (decision.decision, decision.actuator) == ("IRRIGATION_ON", "WATER_PUMP")
    assert decision.notify_farmer is True
    assert "bacterial_spot" in decision.reason


def test_no_leaf_and_no_sensor_is_not_a_score():
    with pytest.raises(NothingToScore):
        compute_gpss(damage_percentage=None)


def test_sensors_alone_are_scored_without_a_leaf():
    gpss = compute_gpss(damage_percentage=None, soil_moisture=20.0, temperature=24.0)
    assert gpss.signals["damage"] is False
    assert gpss.sub_scores["damage_score"] is None
    assert gpss.stress_type == "Water Stress"


# --- through the API ------------------------------------------------------------


def test_disease_reaches_both_clients(client, auth, site):
    at = datetime.now(timezone.utc) - timedelta(hours=3)
    res = client.post(
        "/api/v1/ingest/capture",
        json=_body("dx-blight", at=at, score=93.4, diagnosis=_diagnosis(
            "late_blight", 0.97,
            top=[{"code": "late_blight", "p": 0.97}, {"code": "early_blight", "p": 0.02},
                 {"code": "target_spot", "p": 0.01}],
        )),
        headers=site["node"],
    )
    assert res.status_code == 200, res.text
    assert res.json()["decision"] == "ALERT_AGRONOMIST"
    assert res.json()["notify_farmer"] is True

    capture = client.get(f"/api/v1/sites/{site['id']}/captures", headers=auth).json()[0]
    dx = capture["diagnosis"]
    assert dx["status"] == "ok" and dx["code"] == "late_blight" and dx["crop"] == "tomato"
    assert dx["disease_found"] is True and dx["uncertain"] is False and dx["healthy"] is False
    assert [a["code"] for a in dx["alternatives"]] == ["early_blight", "target_spot"]
    assert capture["label"] == "late_blight"


def test_dark_frame_keeps_the_greenhouse_scored(client, auth, site):
    """Night: the photo is unreadable but the soil is dry. The reading is kept,
    scored from the sensors, and irrigation still runs."""
    at = datetime.now(timezone.utc) - timedelta(hours=1)
    res = client.post(
        "/api/v1/ingest/capture",
        json=_body("dx-night", at=at, diagnosis=_unreadable("too_dark"),
                   sensors={"temperature": 19.0, "humidity": 80.0, "soil_moisture": 8.0}),
        headers=site["node"],
    )
    assert res.status_code == 200, res.text
    assert res.json()["decision"] == "IRRIGATION_ON"

    live = client.get(f"/api/v1/sites/{site['id']}/live", headers=auth).json()
    capture = live["capture"]
    assert capture["node_capture_id"] == "dx-night"
    assert capture["risk_score"] is None and capture["risk_level"] is None
    assert capture["signals"]["damage"] is False
    assert capture["sub_scores"]["damage_score"] is None
    assert capture["diagnosis"] == {
        "status": "unreadable", "crop": "tomato", "code": None, "confidence": None,
        "healthy": None, "uncertain": False, "disease_found": False, "reason": "too_dark",
        "alternatives": [], "model": "tomato_clean_v1",
    }
    # The afternoon's finding stays on the dashboard.
    assert live["last_leaf_capture"]["node_capture_id"] == "dx-blight"
    assert live["last_leaf_capture"]["diagnosis"]["code"] == "late_blight"


def test_leaf_risk_series_skips_unreadable_frames(client, auth, site):
    series = client.get(
        f"/api/v1/sites/{site['id']}/series", params={"metric": "risk_score"}, headers=auth
    ).json()
    assert [p["v"] for p in series["points"]] == [93.4]


def test_readable_leaf_clears_last_leaf(client, auth, site):
    at = datetime.now(timezone.utc) - timedelta(minutes=30)
    client.post(
        "/api/v1/ingest/capture",
        json=_body("dx-healthy", at=at, score=0.4, diagnosis=_diagnosis("healthy", 0.99)),
        headers=site["node"],
    )
    live = client.get(f"/api/v1/sites/{site['id']}/live", headers=auth).json()
    assert live["capture"]["diagnosis"]["healthy"] is True
    assert live["last_leaf_capture"] is None


def test_unreadable_with_no_sensors_is_refused_and_leaves_nothing(client, auth, site):
    before = len(client.get(f"/api/v1/sites/{site['id']}/captures", headers=auth).json())
    res = client.post(
        "/api/v1/ingest/capture",
        json=_body("dx-empty", at=datetime.now(timezone.utc), diagnosis=_unreadable("no_leaf"),
                   sensors=None, image_b64="/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
                   "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
                   "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="),
        headers=site["node"],
    )
    # 422 is one of the codes the Pi's outbox files as undeliverable.
    assert res.status_code == 422
    assert res.json()["detail"] == "nothing_to_score"
    assert len(client.get(f"/api/v1/sites/{site['id']}/captures", headers=auth).json()) == before
    # The photo was written before scoring failed; it must not be left behind.
    assert not list((settings.data_dir / site["id"] / "captures").glob("dx-empty.*"))


def test_no_verdict_without_an_unreadable_diagnosis_is_still_refused(client, site):
    body = _body("dx-silent", at=datetime.now(timezone.utc), diagnosis=_diagnosis("healthy", 0.9))
    body["risk_score"] = body["risk_level"] = None
    res = client.post("/api/v1/ingest/capture", json=body, headers=site["node"])
    assert res.status_code == 400
    assert res.json()["detail"] == "risk_score_or_level_required"

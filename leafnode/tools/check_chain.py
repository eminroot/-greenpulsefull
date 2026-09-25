"""End to end: real GreenPulse server + real LeafNode Pi service, over HTTP.

Starts both as real processes on a laptop and walks ESP32 -> Pi -> server ->
phone, including the failures found in the 2026-09-24 review: an unkeyed frame
from the LAN, a poison row in the outbox, the leaf photo reaching the app, a
phone scan whose verdict arrives twice, and agent.py answering a scan.

Since 2026-09-25 the Pi runs the ML team's trained classifier, not the
placeholder, and the chain also checks real leaves: a late blight leaf alerts
the farmer even with perfect sensors, a healthy one does not, a dark night
frame still delivers its sensors, and a dark phone scan asks for a retake.

Since the photo-on-request feature, a stand-in for the ESP32's /capture checks
the "take a photo now" road: app -> server job -> agent -> Pi asks the camera
-> photo, score and sensors come back to the app; and a camera that refuses the
key or does not answer ends the request with a reason, not a silent wait.

    python tools/check_chain.py

Run it with a Python that has pi/requirements.txt installed. The server folder
defaults to ../server, next to this folder in the GreenPulse repository
(GREENPULSE_SERVER_DIR). The real leaf photos come from the ML team's
validation set (GREENPULSE_ML_DIR, default ../GreenPulse 1/GreenPulse); without
it those checks are skipped, not failed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

PI_DIR = Path(__file__).resolve().parent.parent / "pi"
SERVER_DIR = Path(
    os.environ.get(
        "GREENPULSE_SERVER_DIR",
        Path(__file__).resolve().parents[2] / "server",
    )
)
SERVER_PY = next(
    (
        p
        for p in (SERVER_DIR / ".venv" / "Scripts" / "python.exe", SERVER_DIR / ".venv" / "bin" / "python")
        if p.exists()
    ),
    Path(sys.executable),
)
ML_DIR = Path(
    os.environ.get(
        "GREENPULSE_ML_DIR",
        Path(__file__).resolve().parents[2] / "GreenPulse 1" / "GreenPulse",
    )
)
VAL = ML_DIR / "datasets" / "processed" / "tomato_hybrid_v1" / "val"
S_PORT, P_PORT, CAM_PORT = 8111, 8112, 8113
S = f"http://127.0.0.1:{S_PORT}"
P = f"http://127.0.0.1:{P_PORT}"
NODE_KEY = os.environ.get("E2E_NODE_KEY", "e2e-node-key-0123456789abcdef")

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"{'  ok  ' if ok else '  FAIL'} {label}{'  -> ' + detail if detail else ''}", flush=True)


def wait_up(url: str, proc: subprocess.Popen, log: Path) -> None:
    for _ in range(80):
        if proc.poll() is not None:
            print(log.read_text(encoding="utf-8", errors="replace"))
            raise SystemExit(f"{url} died on start")
        try:
            if requests.get(url, timeout=1).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise SystemExit(f"{url} never came up")


def val_leaf(folder: str) -> bytes | None:
    """First validation photo of a class, or None when the ML package is absent."""
    files = sorted((VAL / folder).glob("*.jpg")) if (VAL / folder).is_dir() else []
    return files[0].read_bytes() if files else None


def dark_jpeg() -> bytes:
    """What the ESP32-CAM sends at night: sensor noise on black."""
    import cv2
    import numpy as np

    img = np.clip(np.random.default_rng(3).normal(6, 3, (600, 800, 3)), 0, 255).astype(np.uint8)
    return cv2.imencode(".jpg", img)[1].tobytes()


def leaf_jpeg() -> bytes:
    import cv2
    import numpy as np

    img = np.full((600, 800, 3), (40, 30, 25), dtype=np.uint8)
    cv2.ellipse(img, (400, 300), (260, 160), 20, 0, 360, (60, 170, 60), -1)
    cv2.ellipse(img, (330, 260), (70, 45), -10, 0, 360, (40, 110, 165), -1)
    return cv2.imencode(".jpg", img)[1].tobytes()


class FakeCamera:
    """The ESP32's web server as firmware 1.2 runs it: /capture checks the node
    key and answers with a JPEG (sensors in X-Sensors, id in X-Device-Id),
    /hello is the Pi checking in, /status answers without a key."""

    SENSORS = {"temperature": 24.0, "humidity": 58.0, "soil_moisture": 44.0}
    FIRMWARE = "1.2.0-e2e"

    def __init__(self, port: int, jpeg: bytes) -> None:
        self.jpeg = jpeg
        self.refuse = False
        self.hits = 0
        self.hellos = 0
        cam = self

        class Handler(BaseHTTPRequestHandler):
            def reply_json(self, body: dict) -> None:
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def status(self) -> dict:
                return {"device_id": "e2e-camera", "firmware": FakeCamera.FIRMWARE, "ip": "127.0.0.1",
                        "ssid": "e2e-wifi", "rssi": -50, "interval_s": 60}

            def do_GET(self) -> None:
                if self.path.split("?")[0] == "/status":
                    self.reply_json(self.status())
                else:
                    self.send_error(404)

            def do_POST(self) -> None:
                path = self.path.split("?")[0]
                if path not in ("/capture", "/hello"):
                    self.send_error(404)
                    return
                if cam.refuse or self.headers.get("X-Node-Key") != NODE_KEY:
                    self.send_response(401)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if path == "/hello":
                    cam.hellos += 1
                    self.reply_json(self.status())
                    return
                cam.hits += 1
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(cam.jpeg)))
                self.send_header("X-Device-Id", "e2e-camera")
                self.send_header("X-Firmware", FakeCamera.FIRMWARE)
                self.send_header("X-Sensors", json.dumps(FakeCamera.SENSORS))
                self.end_headers()
                self.wfile.write(cam.jpeg)

            def log_message(self, *args) -> None:
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="gp-e2e-"))
    s_log, p_log = tmp / "server.log", tmp / "pi.log"

    server = subprocess.Popen(
        [str(SERVER_PY), "-m", "uvicorn", "app.main:app", "--port", str(S_PORT), "--log-level", "warning"],
        cwd=SERVER_DIR,
        env={
            **os.environ,
            "GP_ENV": "e2e",
            "GP_SECRET_KEY": "e2e-secret-key-long-enough-for-hs256-signing-ok",
            "GP_DATABASE_URL": f"sqlite+aiosqlite:///{(tmp / 's.db').as_posix()}",
            "GP_DATA_DIR": str(tmp / "sdata"),
        },
        stdout=s_log.open("w"),
        stderr=subprocess.STDOUT,
    )
    pi = None
    try:
        wait_up(f"{S}/health", server, s_log)

        reg = requests.post(
            f"{S}/api/v1/auth/register",
            json={"email": "farmer@example.com", "password": "greenhouse1"},
        ).json()
        auth = {"Authorization": f"Bearer {reg['access_token']}"}
        site = requests.get(f"{S}/api/v1/sites", headers=auth).json()[0]
        paired = requests.post(
            f"{S}/api/v1/sites/{site['id']}/devices",
            json={"name": "Pi", "kind": "pi"},
            headers=auth,
        ).json()
        token = paired["token"]

        pi = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--port", str(P_PORT), "--log-level", "warning"],
            cwd=PI_DIR,
            env={
                **os.environ,
                "LEAFNODE_MODEL": "greenpulse",
                "LEAFNODE_CROP": "tomato",
                "LEAFNODE_CAPTURES": str(tmp / "pcaps"),
                "LEAFNODE_QUEUE": str(tmp / "queue.db"),
                "LEAFNODE_UPSTREAM_URL": f"{S}/api/v1/ingest/capture",
                "LEAFNODE_UPSTREAM_TOKEN": token,
                "LEAFNODE_UPSTREAM_POLL": "1",
                "LEAFNODE_NODE_KEY": NODE_KEY,
                "LEAFNODE_CAMERAS": str(tmp / "cameras.json"),
                # The stand-in camera listens on loopback, which the Pi does
                # not learn from (that is where agent.py posts from), so it is
                # named here. A real ESP32 is learned from its frames.
                "LEAFNODE_CAMERA_URL": f"http://127.0.0.1:{CAM_PORT}",
                "LEAFNODE_CAMERA_BUDGET": "6",
                # Not leafnode-01: its .local fallback would reach a real board
                # on the same Wi-Fi.
                "LEAFNODE_CAMERA_ID": "e2e-camera",
                # Check in every second, and never sweep the laptop's subnet.
                "LEAFNODE_HELLO_EVERY": "1",
                "LEAFNODE_CAMERA_SCAN": "0",
                "PYTHONUNBUFFERED": "1",
            },
            stdout=p_log.open("w"),
            stderr=subprocess.STDOUT,
        )
        wait_up(f"{P}/health", pi, p_log)
        node = {"X-Node-Key": NODE_KEY}
        jpeg = leaf_jpeg()

        # 0. The trained model, not the placeholder, is what answers.
        model = {}
        for _ in range(40):
            model = requests.get(f"{P}/health").json()["model"]
            if model["loaded"] or model["error"]:
                break
            time.sleep(0.25)
        check("Pi loaded the trained leaf model at startup",
              model.get("loaded") and model.get("version") == "tomato_clean_v1", json.dumps(model))

        def captures() -> list[dict]:
            return requests.get(f"{S}/api/v1/sites/{site['id']}/captures", headers=auth).json()

        def depth() -> int:
            return requests.get(f"{P}/health").json()["upstream"]["queue_depth"]

        def drain(timeout: float = 15) -> int:
            end = time.time() + timeout
            while time.time() < end and depth() > 0:
                time.sleep(0.3)
            return depth()

        # 1. The LAN is not trusted: /analyze without the node key is refused.
        anon = requests.post(f"{P}/analyze", files={"image": ("leaf.jpg", jpeg, "image/jpeg")},
                             data={"device_id": "intruder"}, timeout=30)
        check("Pi refuses a frame without the node key", anon.status_code == 401, f"HTTP {anon.status_code}")

        # 2. A malformed sensor blob (JSON, but not an object) must not poison the queue.
        bad = requests.post(
            f"{P}/analyze",
            files={"image": ("leaf.jpg", jpeg, "image/jpeg")},
            data={"device_id": "leafnode-01", "sensor": "[1, 2, 3]"},
            headers=node, timeout=30,
        )
        check("Pi still scores a frame with a bad sensor blob", bad.status_code == 200, f"HTTP {bad.status_code}")

        # 3. A normal ESP32 frame right behind it.
        good = requests.post(
            f"{P}/analyze",
            files={"image": ("leaf.jpg", jpeg, "image/jpeg")},
            data={"device_id": "leafnode-01",
                  "sensor": json.dumps({"temperature": 29.4, "humidity": 48.0, "soil_moisture": 26.5})},
            headers=node, timeout=30,
        )
        check("Pi scores a normal frame", good.status_code == 200, good.text[:120])
        left = drain()
        check("Pi outbox drains (no head-of-line block)", left == 0, f"queue depth {left}")

        caps = captures()
        good_id = good.json().get("capture_id")
        stored = next((c for c in caps if c["node_capture_id"] == good_id), None)
        check("normal frame reaches the server", stored is not None, f"{len(caps)} captures on server")
        if stored:
            check("server fused the sensors", stored["reading"] is not None and stored["signals"]["water"])
            check("leaf photo reaches the farmer", bool(stored["image_url"]), f"image_url={stored['image_url']}")
            if stored["image_url"]:
                img = requests.get(f"{S}{stored['image_url']}", headers=auth)
                check("photo bytes match what the ESP32 sent", img.content == jpeg, f"{len(img.content)} bytes")

        # 3b. A row the server will always refuse must not block the ones behind it.
        import sqlite3

        with sqlite3.connect(tmp / "queue.db") as q:
            q.execute("INSERT INTO outbox (payload, created_at) VALUES (?, ?)",
                      (json.dumps({"capture_id": "../../etc/passwd", "risk_score": 5}), time.time()))
        after = requests.post(
            f"{P}/analyze", files={"image": ("leaf.jpg", jpeg, "image/jpeg")},
            data={"device_id": "leafnode-01"}, headers=node, timeout=30,
        ).json()
        left = drain()
        dead = requests.get(f"{P}/health").json()["upstream"]["dead_letters"]
        arrived = any(c["node_capture_id"] == after["capture_id"] for c in captures())
        check("refused row goes to dead_letter, next reading still arrives",
              left == 0 and dead == 1 and arrived, f"depth={left} dead={dead} arrived={arrived}")

        # 4. Phone scan where the outbox beats the agent's direct report.
        sub = requests.post(
            f"{S}/api/v1/sites/{site['id']}/scans",
            files={"image": ("leaf.jpg", jpeg, "image/jpeg")}, headers=auth,
        ).json()
        dev = {"Authorization": f"Bearer {token}"}
        job = requests.get(f"{S}/api/v1/ingest/jobs", params={"wait": 3}, headers=dev).json()
        photo = requests.get(f"{S}{job['image_url']}", headers=dev).content
        verdict = requests.post(
            f"{P}/analyze",
            files={"image": ("leaf.jpg", photo, "image/jpeg")},
            data={"device_id": "leafnode-01", "job_id": job["job_id"]},
            headers=node, timeout=30,
        ).json()
        drain()  # the outbox delivers first
        late = requests.post(
            f"{S}/api/v1/ingest/capture",
            json={"capture_id": verdict["capture_id"], "job_id": job["job_id"], "device_id": "leafnode-01",
                  "risk_score": verdict["risk_score"], "risk_level": verdict["risk_level"]},
            headers=dev,
        ).json()
        status = requests.get(f"{S}/api/v1/scans/{sub['job_id']}", headers=auth).json()
        check("phone scan completes even when the outbox wins the race",
              status["status"] == "done", f"job={status['status']} report={late.get('status')}")
        if status.get("capture"):
            check("phone scan keeps the farmer's photo", bool(status["capture"]["image_url"]))
            check("phone scan is labelled as a phone scan", status["capture"]["source"] == "phone",
                  status["capture"]["source"])

        # 5. A model returning numpy scalars / out of range numbers must not break delivery.
        #    (exercised through the sanitiser directly; the live model is the placeholder)
        sys.path.insert(0, str(PI_DIR))
        try:
            import numpy as np
            from server import sanitise_result  # type: ignore
            from model import RiskResult  # type: ignore

            weird = RiskResult(np.float32(131.7), "EXTREME", "x" * 500, np.float64(1.4), "v" * 300,
                               {"arr": np.arange(3), "f": np.float32(0.5)})
            clean = sanitise_result(weird)
            json.dumps(clean)
            check("model output is normalised before it is queued",
                  clean["risk_score"] == 100.0 and clean["risk_level"] == "critical"
                  and clean["confidence"] == 1.0 and len(clean["label"]) <= 120,
                  json.dumps({k: clean[k] for k in ("risk_score", "risk_level", "confidence")}))
        except ImportError as exc:
            check("model output is normalised before it is queued", False, f"no sanitiser: {exc}")

        # 6. Real leaves through the whole chain.
        ideal = json.dumps({"temperature": 23.0, "humidity": 60.0, "soil_moisture": 58.0, "light": 600.0})

        def through_chain(photo: bytes, sensors: str | None) -> tuple[dict, dict | None]:
            data = {"device_id": "leafnode-01"}
            if sensors:
                data["sensor"] = sensors
            reply = requests.post(f"{P}/analyze", files={"image": ("leaf.jpg", photo, "image/jpeg")},
                                  data=data, headers=node, timeout=60).json()
            drain()
            stored = next((c for c in captures() if c["node_capture_id"] == reply["capture_id"]), None)
            return reply, stored

        blight, healthy = val_leaf("Tomato___Late_blight"), val_leaf("Tomato___healthy")
        if blight and healthy:
            reply, stored = through_chain(blight, ideal)
            dx = (stored or {}).get("diagnosis") or {}
            check("late blight leaf is diagnosed on the Pi and reaches the app",
                  reply.get("label") == "late_blight" and dx.get("code") == "late_blight"
                  and dx.get("disease_found") is True,
                  f"pi={reply.get('label')} {reply.get('confidence')} server={dx.get('code')}")
            check("a sure disease alerts the farmer even with perfect sensors",
                  stored is not None and stored["decision"] == "ALERT_AGRONOMIST"
                  and stored["notify_farmer"] and stored["actuator"] == "NONE",
                  f"gpss={stored and stored['gpss_score']} decision={stored and stored['decision']}")

            reply, stored = through_chain(healthy, ideal)
            dx = (stored or {}).get("diagnosis") or {}
            check("healthy leaf is read as healthy and does not alert",
                  dx.get("code") == "healthy" and stored is not None and stored["decision"] == "MONITORING",
                  f"code={dx.get('code')} {dx.get('confidence')} decision={stored and stored['decision']}")
        else:
            print(f"  skip real-leaf checks: no validation photos under {VAL}")

        # 7. Night: the frame is black, the sensors still matter.
        dry_night = json.dumps({"temperature": 18.0, "humidity": 85.0, "soil_moisture": 8.0})
        reply, stored = through_chain(dark_jpeg(), dry_night)
        check("dark frame is refused as unreadable, not diagnosed",
              reply.get("unreadable") == "too_dark" and reply.get("risk_score") is None,
              json.dumps({k: reply.get(k) for k in ("unreadable", "risk_score", "label", "queued")}))
        check("its sensors still reach the server and still irrigate",
              stored is not None and stored["risk_score"] is None
              and stored["diagnosis"]["status"] == "unreadable" and stored["decision"] == "IRRIGATION_ON",
              f"decision={stored and stored['decision']} damage={stored and stored['sub_scores']['damage_score']}")
        live = requests.get(f"{S}/api/v1/sites/{site['id']}/live", headers=auth).json()
        last = (live.get("last_leaf_capture") or {}).get("diagnosis") or {}
        check("the dashboard keeps the last leaf it could read",
              last.get("status") == "ok", f"last_leaf={last.get('code')}")

        empty = requests.post(f"{P}/analyze", files={"image": ("leaf.jpg", dark_jpeg(), "image/jpeg")},
                              data={"device_id": "leafnode-01"}, headers=node, timeout=60).json()
        check("a dark frame with no sensors is not sent upstream", empty.get("queued") is False,
              json.dumps({k: empty.get(k) for k in ("unreadable", "queued")}))

        # 8. The real agent.py answering a scan the farmer takes in the app.
        a_log = tmp / "agent.log"
        agent = subprocess.Popen(
            [sys.executable, "agent.py"], cwd=PI_DIR,
            env={**os.environ, "LEAFNODE_UPSTREAM_URL": f"{S}/api/v1/ingest/capture",
                 "LEAFNODE_UPSTREAM_TOKEN": token, "LEAFNODE_NODE_KEY": NODE_KEY,
                 "LEAFNODE_PORT": str(P_PORT), "GREENPULSE_POLL_WAIT": "5", "PYTHONUNBUFFERED": "1"},
            stdout=a_log.open("w"), stderr=subprocess.STDOUT,
        )
        try:
            t0 = time.time()
            sub = requests.post(f"{S}/api/v1/sites/{site['id']}/scans",
                                files={"image": ("leaf.jpg", jpeg, "image/jpeg")}, headers=auth).json()
            status = {}
            while time.time() - t0 < 20:
                status = requests.get(f"{S}/api/v1/scans/{sub['job_id']}", headers=auth).json()
                if status["status"] in ("done", "failed", "expired"):
                    break
                time.sleep(0.2)
            check("agent.py answers a phone scan end to end", status.get("status") == "done",
                  f"{status.get('status')} in {time.time() - t0:.1f}s")

            # A phone photo taken in the dark: the farmer is told to retake it.
            t0 = time.time()
            sub = requests.post(f"{S}/api/v1/sites/{site['id']}/scans",
                                files={"image": ("leaf.jpg", dark_jpeg(), "image/jpeg")}, headers=auth).json()
            status = {}
            while time.time() - t0 < 20:
                status = requests.get(f"{S}/api/v1/scans/{sub['job_id']}", headers=auth).json()
                if status["status"] in ("done", "failed", "expired"):
                    break
                time.sleep(0.2)
            check("a dark phone scan fails with a reason the app can explain",
                  status.get("status") == "failed" and status.get("error") == "unreadable:too_dark",
                  f"{status.get('status')} error={status.get('error')}")

            # 9. "Take a photo now": the greenhouse camera is asked, not the phone.
            shot = blight or jpeg
            camera = FakeCamera(CAM_PORT, shot)

            def camera_request(timeout: float = 30) -> tuple[dict, dict, float]:
                t0 = time.time()
                sub = requests.post(f"{S}/api/v1/sites/{site['id']}/camera/capture", headers=auth).json()
                status = {}
                while time.time() - t0 < timeout:
                    status = requests.get(f"{S}/api/v1/scans/{sub['job_id']}", headers=auth).json()
                    if status["status"] in ("done", "failed", "expired"):
                        break
                    time.sleep(0.2)
                return sub, status, time.time() - t0

            try:
                for _ in range(40):
                    cam_info = requests.get(f"{P}/health").json()["cameras"].get("e2e-camera", {})
                    if cam_info.get("firmware"):
                        break
                    time.sleep(0.25)
                check("the Pi checks in with the camera and knows its firmware",
                      camera.hellos > 0 and cam_info.get("firmware") == FakeCamera.FIRMWARE
                      and cam_info.get("on_request") is True,
                      json.dumps({k: cam_info.get(k) for k in ("firmware", "on_request", "ssid")}))

                sub, status, took = camera_request()
                check("a photo on request is taken by the camera and comes back scored",
                      sub.get("kind") == "camera" and status.get("status") == "done"
                      and camera.hits == 1,
                      f"{status.get('status')} in {took:.1f}s, camera asked {camera.hits}x, "
                      f"error={status.get('error')}")
                cap = status.get("capture") or {}
                if cap:
                    img = requests.get(f"{S}{cap['image_url']}", headers=auth) if cap.get("image_url") else None
                    check("the camera's photo reaches the app, byte for byte",
                          img is not None and img.content == shot,
                          f"image_url={cap.get('image_url')} {len(img.content) if img else 0} bytes")
                    check("its risk score and the camera's sensors arrive with it",
                          cap.get("risk_score") is not None
                          and (cap.get("reading") or {}).get("soil_moisture") == 44.0,
                          f"risk={cap.get('risk_score')} reading={cap.get('reading')}")
                    check("it is labelled as the greenhouse camera's frame", cap.get("source") == "node",
                          str(cap.get("source")))
                    live = requests.get(f"{S}/api/v1/sites/{site['id']}/live", headers=auth).json()
                    check("the dashboard shows it as the newest reading",
                          (live.get("capture") or {}).get("id") == cap.get("id"))

                camera.refuse = True
                _, status, _ = camera_request()
                check("a camera that refuses the node key ends the request with a reason",
                      status.get("status") == "failed" and status.get("error") == "camera_refused",
                      f"{status.get('status')} error={status.get('error')}")
            finally:
                camera.stop()

            _, status, took = camera_request()
            check("a camera that does not answer ends the request with a reason",
                  status.get("status") == "failed" and status.get("error") == "camera_unreachable",
                  f"{status.get('status')} error={status.get('error')} in {took:.1f}s")

            # 10. Old firmware: the camera keeps posting frames but has no photo
            #     server. The farmer is told so at once, not after the retries.
            requests.post(f"{P}/analyze", files={"image": ("leaf.jpg", jpeg, "image/jpeg")},
                          data={"device_id": "e2e-camera"}, headers=node, timeout=30)
            _, status, took = camera_request()
            check("a camera on old firmware says so within seconds",
                  status.get("status") == "failed" and status.get("error") == "camera_outdated"
                  and took < 4,
                  f"{status.get('status')} error={status.get('error')} in {took:.1f}s")
        finally:
            agent.terminate()
            agent.wait(timeout=10)
            print("--- agent log ---\n" + a_log.read_text(encoding="utf-8", errors="replace"))

    finally:
        for proc in (pi, server):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("\n--- pi log (tail) ---")
        print("\n".join(p_log.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

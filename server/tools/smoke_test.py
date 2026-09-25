"""End to end check against a real running server.

Starts uvicorn, then walks the exact path production takes:

    register a grower -> pair a node -> node uploads a scored leaf ->
    the phone reads it back -> the phone is pushed the next one live ->
    the phone submits its own photo -> the node picks it up and answers

Run it after deploying, pointed at the real server, to prove the chain works:

    python tools/smoke_test.py                       # starts its own server
    python tools/smoke_test.py https://your-host     # tests a deployed one
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import websockets

ROOT = Path(__file__).resolve().parent.parent
PASS = "  ok   "
FAIL = "  FAIL "

TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010101006000600000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc40014000100000000000000000000000000000009ffc40014100100000000000000000000000000000000ffda0008010100003f0029ffd9"
)

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    print(f"{PASS if ok else FAIL} {label}{(' - ' + detail) if detail and not ok else ''}")
    if not ok:
        _failures.append(label)
    return ok


def start_server(port: int, workdir: Path) -> subprocess.Popen:
    env = {
        **os.environ,
        "GP_ENV": "smoke",
        "GP_SECRET_KEY": "smoke-test-secret-key-long-enough-for-hs256",
        "GP_DATABASE_URL": f"sqlite+aiosqlite:///{(workdir / 'smoke.db').as_posix()}",
        "GP_DATA_DIR": str(workdir / "data"),
    }
    # Logs go to a file, never to an unread pipe: once a pipe buffer fills, the
    # server blocks on its own logging and the run hangs for no visible reason.
    log_path = workdir / "server.log"
    log_file = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "info"],
        cwd=ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    for _ in range(100):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=1).status_code == 200:
                print(f"server log: {log_path}\n")
                return proc
        except httpx.HTTPError:
            pass
        if proc.poll() is not None:
            print(log_path.read_text(encoding="utf-8", errors="replace"))
            raise RuntimeError("server exited during startup")
        time.sleep(0.2)
    raise RuntimeError("server did not come up")


async def run(base: str) -> None:
    ws_base = base.replace("https://", "wss://").replace("http://", "ws://")
    stamp = int(time.time() * 1000)

    async with httpx.AsyncClient(base_url=base, timeout=30) as http:
        # --- the grower signs up ------------------------------------------
        res = await http.post(
            "/api/v1/auth/register",
            json={
                "email": f"smoke-{stamp}@example.com",
                "password": "greenhouse1",
                "name": "Smoke Grower",
            },
        )
        if not check("grower registers", res.status_code == 201, res.text):
            return
        access = res.json()["access_token"]
        auth = {"Authorization": f"Bearer {access}"}

        sites = (await http.get("/api/v1/sites", headers=auth)).json()
        check("default greenhouse created", bool(sites))
        site_id = sites[0]["id"]

        # --- the dashboard before any hardware reports --------------------
        live = (await http.get(f"/api/v1/sites/{site_id}/live", headers=auth)).json()
        check(
            "empty dashboard shows nothing rather than fake numbers",
            live["capture"] is None and live["reading"] is None and live["online"] is False,
        )

        # --- pair the Raspberry Pi ----------------------------------------
        paired = await http.post(
            f"/api/v1/sites/{site_id}/devices",
            json={"name": "Greenhouse Pi", "kind": "pi"},
            headers=auth,
        )
        if not check("node pairs and gets a token", paired.status_code == 201, paired.text):
            return
        node_token = paired.json()["token"]
        node = {"Authorization": f"Bearer {node_token}"}

        health = await http.get("/api/v1/ingest/health", headers=node)
        check("node token authenticates", health.status_code == 200, health.text)

        bad = await http.get(
            "/api/v1/ingest/health", headers={"Authorization": "Bearer gp_wrong"}
        )
        check("a wrong node token is refused", bad.status_code == 401)

        # --- a live dashboard is open -------------------------------------
        # The socket takes a one minute ticket, never the access token.
        ticket = (
            await http.post(f"/api/v1/sites/{site_id}/stream/ticket", headers=auth)
        ).json()["ticket"]
        async with websockets.connect(
            f"{ws_base}/api/v1/sites/{site_id}/stream?ticket={ticket}"
        ) as ws:
            ready = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            check("dashboard websocket opens", ready.get("type") == "ready")

            # --- the node uploads a scored leaf ---------------------------
            upload = await http.post(
                "/api/v1/ingest/capture",
                json={
                    "capture_id": f"smoke-{stamp}",
                    "site_id": "site-01",
                    "device_id": "leafnode-01",
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": 173.4,
                    "sensors": {
                        "temperature": 24.2,
                        "humidity": 58.0,
                        "soil_moisture": 52.0,
                    },
                    "risk_score": 22.0,
                    "risk_level": "low",
                    "label": "healthy",
                    "confidence": 0.88,
                    "model_version": "leafnode-placeholder-1",
                },
                headers=node,
            )
            check("node upload accepted", upload.status_code == 200, upload.text)

            pushed = None
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                message = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if message.get("type") == "capture":
                    pushed = message
                    break
            check("reading pushed to the open dashboard", pushed is not None)
            if pushed:
                check(
                    "pushed reading carries the real sensor values",
                    pushed["capture"]["reading"]["temperature"] == 24.2
                    and pushed["capture"]["reading"]["soil_moisture"] == 52.0,
                )
                check(
                    "missing light probe reported as absent, not zero",
                    pushed["capture"]["reading"]["light"] is None
                    and pushed["capture"]["signals"]["light"] is False,
                )

        # --- the phone reads it back --------------------------------------
        live = (await http.get(f"/api/v1/sites/{site_id}/live", headers=auth)).json()
        check(
            "dashboard now shows the node reading",
            live["capture"] is not None
            and live["capture"]["risk_score"] == 22.0
            and live["reading"]["temperature"] == 24.2,
        )
        check("greenhouse reports online", live["online"] is True)

        # --- redelivery after an outage must not duplicate ----------------
        again = await http.post(
            "/api/v1/ingest/capture",
            json={
                "capture_id": f"smoke-{stamp}",
                "risk_score": 22.0,
                "risk_level": "low",
                "sensors": {"temperature": 24.2, "humidity": 58.0, "soil_moisture": 52.0},
            },
            headers=node,
        )
        check("queued redelivery is not stored twice", again.json().get("status") == "duplicate")

        # --- the farmer photographs a leaf in the app ---------------------
        submitted = await http.post(
            f"/api/v1/sites/{site_id}/scans",
            files={"image": ("leaf.jpg", TINY_JPEG, "image/jpeg")},
            headers=auth,
        )
        if not check("phone scan queued", submitted.status_code == 202, submitted.text):
            return
        job_id = submitted.json()["job_id"]

        claimed = await http.get("/api/v1/ingest/jobs", params={"wait": 5}, headers=node)
        check("node claims the phone scan", claimed.status_code == 200 and claimed.json()["job_id"] == job_id)

        photo = await http.get(claimed.json()["image_url"], headers=node)
        check("node downloads the exact photo the farmer took", photo.content == TINY_JPEG)

        answered = await http.post(
            "/api/v1/ingest/capture",
            json={
                "capture_id": f"smoke-scan-{stamp}",
                "job_id": job_id,
                "risk_score": 41.0,
                "risk_level": "medium",
                "label": "early_blight",
                "confidence": 0.77,
                "sensors": {"temperature": 24.2, "humidity": 58.0, "soil_moisture": 52.0},
            },
            headers=node,
        )
        check("node answers the scan", answered.status_code == 200, answered.text)

        status = (await http.get(f"/api/v1/scans/{job_id}", headers=auth)).json()
        check(
            "phone sees the finished scan",
            status["status"] == "done" and status["capture"]["risk_score"] == 41.0,
        )

        # --- history and savings ------------------------------------------
        captures = (
            await http.get(f"/api/v1/sites/{site_id}/captures", headers=auth)
        ).json()
        check("history holds both readings", len(captures) == 2)

        series = (
            await http.get(
                f"/api/v1/sites/{site_id}/series",
                params={"metric": "temperature", "hours": 24},
                headers=auth,
            )
        ).json()
        check("trend series returns real points", len(series["points"]) == 2)

        sus = (
            await http.get(f"/api/v1/sites/{site_id}/sustainability", headers=auth)
        ).json()
        check(
            "savings counters start from real events, not a baseline",
            sus["captures"] == 2 and sus["autonomous_actions"] == 0,
        )

        # --- isolation -----------------------------------------------------
        other = (
            await http.post(
                "/api/v1/auth/register",
                json={"email": f"other-{stamp}@example.com", "password": "greenhouse1"},
            )
        ).json()
        peek = await http.get(
            f"/api/v1/sites/{site_id}/live",
            headers={"Authorization": f"Bearer {other['access_token']}"},
        )
        check("another grower cannot read this greenhouse", peek.status_code == 404)


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else None
    proc = None
    tmp = None

    if target is None:
        tmp = tempfile.mkdtemp(prefix="greenpulse-smoke-")
        port = 8731
        target = f"http://127.0.0.1:{port}"
        print(f"starting a server on {target}\n")
        proc = start_server(port, Path(tmp))
    else:
        print(f"testing {target}\n")

    try:
        asyncio.run(run(target))
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)

    print()
    if _failures:
        print(f"{len(_failures)} check(s) failed: {', '.join(_failures)}")
        return 1
    print("every check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
LeafNode Pi service.

Receives a JPEG from the ESP32-CAM, runs whatever model is registered in
model.py, answers the node with a compact risk verdict, and queues the full
record for delivery to your server.

It can also ask the camera for a photo on the spot (POST /capture). agent.py
uses that when the farmer taps "take a photo now" in the app. The camera's
address is learned from the frames it posts here, so nothing is configured.

Run:
    cd pi
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env    # then edit it
    set -a && . ./.env && set +a
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import hmac
import json
import math
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

# OpenCV will happily allocate gigabytes for a JPEG whose header lies about its
# size. Cap it before cv2 is imported, which is when the limit is read.
os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(50_000_000))

import cv2
import numpy as np
import requests
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

import uploader
from model import RISK_BANDS, RiskResult, band_for, load_model, model_info

CAPTURE_DIR = os.path.abspath(os.environ.get("LEAFNODE_CAPTURES", "data/captures"))
# Where each camera was last heard from, so a restart of this service does not
# forget how to reach it before its next scheduled frame.
CAMERAS_PATH = os.path.abspath(os.environ.get("LEAFNODE_CAMERAS", "data/cameras.json"))
# The camera to ask when a request does not name one. Matches DEVICE_ID in the
# firmware's config.h.
CAMERA_ID = os.environ.get("LEAFNODE_CAMERA_ID", "leafnode-01").strip()
# Only for networks where the Pi cannot see the camera's own address, e.g.
# http://192.168.1.124. Normally blank: the address is learned.
CAMERA_URL = os.environ.get("LEAFNODE_CAMERA_URL", "").strip().rstrip("/")
# How long a photo on request may take in all, retries included. The camera
# cannot answer while it is uploading its own scheduled frame, which takes a
# second or two, so a short wait and a retry is normal.
CAMERA_BUDGET_S = float(os.environ.get("LEAFNODE_CAMERA_BUDGET", "40"))
KEEP_CAPTURES = os.environ.get("LEAFNODE_KEEP_CAPTURES", "1") == "1"
SITE_ID = os.environ.get("LEAFNODE_SITE_ID", "site-01")
# Shared with the ESP32 (NODE_KEY in its secrets.h). Anything on the greenhouse
# Wi-Fi can reach this port, and whatever it posts gets signed with the device
# token and lands in the farmer's app, so the key is required, not optional.
NODE_KEY = os.environ.get("LEAFNODE_NODE_KEY", "").strip()
# Matches the server's own limit, so a phone photo the server accepted is never
# refused here.
MAX_IMAGE_BYTES = int(os.environ.get("LEAFNODE_MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))

# Ids end up in filenames and in the server's records, so they are checked
# rather than cleaned: a surprising id is a visible 400, not a silent rename.
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

# No CORS middleware: nothing legitimate calls this from a browser, and allowing
# every origin let any web page opened on the LAN post fake readings.
app = FastAPI(title="LeafNode Pi Service", version="1.2.0", docs_url=None, redoc_url=None)

_started_at = time.time()
_stats = {
    "analyzed": 0,
    "unreadable": 0,
    "failed": 0,
    "rejected": 0,
    "on_request": 0,
    "camera_errors": 0,
    "last_result": None,
}


def require_node_key(x_node_key: str | None = Header(default=None)) -> None:
    if not NODE_KEY:
        raise HTTPException(status_code=503, detail="LEAFNODE_NODE_KEY is not set on the Pi")
    if not x_node_key or not hmac.compare_digest(x_node_key.encode(), NODE_KEY.encode()):
        _stats["rejected"] += 1
        raise HTTPException(status_code=401, detail="Bad or missing node key")


@app.on_event("startup")
def _startup() -> None:
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    _load_cameras()
    uploader.start_worker()
    if not NODE_KEY:
        print("[server] LEAFNODE_NODE_KEY is empty: every /analyze call will be refused. "
              "Run setup.sh or set it in .env.", flush=True)
    # The model loads in the background rather than blocking startup, so the
    # service still comes up when the weights are missing and /health can say
    # that is the problem. Warming it means the first leaf is not the slow one.
    threading.Thread(target=_warm_model, name="leafnode-warmup", daemon=True).start()
    print(f"[server] ready, model config: {model_info()}", flush=True)


def _warm_model() -> None:
    try:
        model = load_model()
        # One throwaway frame so onnxruntime allocates its buffers now.
        model.predict(np.zeros((224, 224, 3), dtype=np.uint8), None)
    except Exception as exc:
        print(f"[server] model failed to load: {exc}. /analyze will answer 503 until it is fixed.",
              flush=True)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "leafnode-pi",
        "site_id": SITE_ID,
        "uptime_s": round(time.time() - _started_at, 1),
        "node_key_set": bool(NODE_KEY),
        "model": model_info(),
        "upstream": {
            "configured": bool(uploader.UPSTREAM_URL),
            "url": uploader.UPSTREAM_URL or None,
            "queue_depth": uploader.queue_depth(),
            "dead_letters": uploader.dead_letter_count(),
        },
        "cameras": dict(_cameras),
        "camera_url_override": CAMERA_URL or None,
        "stats": _stats,
    }


# ---------------------------------------------------------------------------
# Cameras. Each ESP32 posts its frames here, which tells us its address; that
# is the address a photo on request is asked for.
# ---------------------------------------------------------------------------

_cameras: dict[str, dict] = {}
_cameras_lock = threading.Lock()


def _load_cameras() -> None:
    try:
        with open(CAMERAS_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return
    except (OSError, ValueError) as exc:
        print(f"[camera] ignoring unreadable {CAMERAS_PATH}: {exc}", flush=True)
        return
    if isinstance(data, dict):
        with _cameras_lock:
            _cameras.update(
                {k: v for k, v in data.items() if _SAFE_ID.match(k) and isinstance(v, dict)}
            )


def _remember_camera(device_id: str, host: str | None) -> None:
    # The agent posts phone photos from this same Pi. That is not a camera.
    if not host or host in {"127.0.0.1", "::1", "localhost", "testclient"}:
        return
    now = datetime.now(timezone.utc).isoformat()
    with _cameras_lock:
        known = _cameras.get(device_id, {})
        moved = known.get("host") != host
        _cameras[device_id] = {"host": host, "seen_at": now}
        snapshot = dict(_cameras)
    if not moved:
        return
    print(f"[camera] {device_id} is at {host}", flush=True)
    try:
        os.makedirs(os.path.dirname(CAMERAS_PATH), exist_ok=True)
        tmp = CAMERAS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh)
        os.replace(tmp, CAMERAS_PATH)
    except OSError as exc:
        print(f"[camera] could not save {CAMERAS_PATH}: {exc}", flush=True)


def _camera_candidates(device_id: str) -> list[str]:
    """Where to ask, best first: the override, the address its frames came
    from, then its mDNS name (the firmware announces DEVICE_ID.local)."""
    urls = [CAMERA_URL] if CAMERA_URL else []
    with _cameras_lock:
        host = _cameras.get(device_id, {}).get("host")
    if host:
        urls.append(f"http://{host}")
    urls.append(f"http://{device_id}.local")
    return list(dict.fromkeys(urls))


class CameraError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def _photo_from_camera(device_id: str) -> tuple[bytes, str | None, str, str]:
    """Asks the ESP32 to take a photo now. Returns (jpeg, sensor json, the
    device id it reports, the url that answered). Blocking; run it off the
    event loop."""
    deadline = time.monotonic() + CAMERA_BUDGET_S
    tried: list[str] = []
    while True:
        for base in _camera_candidates(device_id):
            left = deadline - time.monotonic()
            if left <= 1:
                break
            try:
                res = requests.post(
                    f"{base}/capture",
                    headers={"X-Node-Key": NODE_KEY},
                    timeout=(min(4.0, left), min(20.0, left)),
                )
            except requests.RequestException as exc:
                tried.append(f"{base}: {type(exc).__name__}")
                continue
            if res.status_code == 401:
                raise CameraError(
                    "camera_refused",
                    f"{base} refused the node key; NODE_KEY in secrets.h must match LEAFNODE_NODE_KEY",
                )
            if res.status_code != 200 or not res.content:
                tried.append(f"{base}: HTTP {res.status_code}")
                continue
            reported = res.headers.get("X-Device-Id", "").strip()
            return (
                res.content,
                res.headers.get("X-Sensors") or None,
                reported if _SAFE_ID.match(reported) else device_id,
                base,
            )
        if deadline - time.monotonic() <= 3:
            raise CameraError("camera_unreachable", "; ".join(tried[-6:]) or "no address to try")
        # Most likely busy sending its scheduled frame. Give it a moment.
        time.sleep(2)


# ---------------------------------------------------------------------------
# Input and output hygiene. The server validates strictly, and a record it
# refuses is a record the farmer never sees, so both ends are cleaned here.
# ---------------------------------------------------------------------------


def _finite(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _jsonable(value: Any, depth: int = 0) -> Any:
    """numpy scalars and arrays, NaN, tuples: everything a model might put in
    `extra` that json.dumps or the server would choke on."""
    if depth > 6:
        return str(value)
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, dict):
        return {str(k)[:64]: _jsonable(v, depth + 1) for k, v in list(value.items())[:64]}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v, depth + 1) for v in list(value)[:256]]
    return str(value)[:200]


def sanitise_result(result: RiskResult) -> dict:
    """Whatever the model returned, turned into something the server accepts.

    model.py is the teammates' file and may be replaced wholesale, so the
    contract is enforced here rather than trusted there.
    """
    unreadable = str(getattr(result, "unreadable", "") or "").strip()[:40] or None
    score = _finite(getattr(result, "risk_score", None))
    if unreadable:
        # The model looked and could not read the frame. No score, on purpose.
        score, level = None, None
    elif score is None:
        raise ValueError("model returned no usable risk_score")
    else:
        score = round(min(100.0, max(0.0, score)), 1)
        level = str(getattr(result, "risk_level", "") or "").strip().lower()
        if level not in RISK_BANDS:
            level = band_for(score)

    confidence = _finite(getattr(result, "confidence", None))
    if confidence is not None:
        confidence = round(min(1.0, max(0.0, confidence)), 3)

    extra = _jsonable(getattr(result, "extra", None) or {})
    if len(json.dumps(extra)) > 8000:
        extra = {"note": "extra was too large to forward"}

    return {
        "risk_score": score,
        "risk_level": level,
        "label": str(getattr(result, "label", "") or "")[:120] or None,
        "confidence": None if unreadable else confidence,
        "model_version": str(getattr(result, "model_version", "") or "")[:120] or None,
        "extra": extra,
        "unreadable": unreadable,
    }


def parse_sensors(raw: str | None, device_id: str) -> dict | None:
    """A malformed sensor blob should not cost us the image, and must not reach
    the server either, where it would be refused and block the queue."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[server] ignoring unparseable sensor payload from {device_id}: {exc}", flush=True)
        return None
    if not isinstance(data, dict):
        print(f"[server] ignoring sensor payload from {device_id}: not an object", flush=True)
        return None

    clean: dict[str, float | int] = {}
    for key, value in list(data.items())[:32]:
        if not isinstance(key, str) or len(key) > 40 or isinstance(value, bool):
            continue
        number = _finite(value)
        if number is None:
            continue
        clean[key] = int(round(number)) if key == "soil_raw" else number
    return clean or None


async def _read_capped(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image too large")
        chunks.append(chunk)
    return b"".join(chunks)


# ---------------------------------------------------------------------------


@app.post("/analyze", dependencies=[Depends(require_node_key)])
async def analyze(
    request: Request,
    image: UploadFile = File(...),
    device_id: str = Form("unknown"),
    sensor: str | None = Form(None),
    # Set by agent.py when the frame is a photo the farmer took in the app. It
    # travels with the record so the server can close that scan out.
    job_id: str | None = Form(None),
) -> JSONResponse:
    received_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    if not _SAFE_ID.match(device_id):
        raise HTTPException(status_code=400, detail="Bad device_id")
    if job_id is not None and not _SAFE_ID.match(job_id):
        raise HTTPException(status_code=400, detail="Bad job_id")

    raw = await _read_capped(image)
    # A frame the ESP32 posted says where the ESP32 is. That is how a photo on
    # request finds it later.
    _remember_camera(device_id, request.client.host if request.client else None)

    reply = await _score(raw, device_id, sensor, job_id, None, received_at, t0)
    return JSONResponse(reply)


@app.post("/capture", dependencies=[Depends(require_node_key)])
async def capture(device_id: str | None = None, job_id: str | None = None) -> JSONResponse:
    """Has the camera take a photo now, then scores it like any other frame.

    agent.py calls this for a "take a photo now" request from the app, with
    the job id; by hand it is a quick way to see the camera work:

        curl -X POST -H "X-Node-Key: $LEAFNODE_NODE_KEY" http://127.0.0.1:8000/capture
    """
    received_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    device_id = (device_id or "").strip() or _default_camera()
    if not _SAFE_ID.match(device_id):
        raise HTTPException(status_code=400, detail="Bad device_id")
    if job_id is not None and not _SAFE_ID.match(job_id):
        raise HTTPException(status_code=400, detail="Bad job_id")

    try:
        raw, sensor, device_id, answered = await run_in_threadpool(_photo_from_camera, device_id)
    except CameraError as exc:
        _stats["camera_errors"] += 1
        print(f"[capture] {device_id}: {exc.code}: {exc}", flush=True)
        # 504 when nobody answered, 502 when the camera answered wrongly. The
        # code is what the farmer's app turns into words.
        status = 504 if exc.code == "camera_unreachable" else 502
        return JSONResponse({"detail": exc.code, "why": str(exc)}, status_code=status)
    if len(raw) > MAX_IMAGE_BYTES:
        _stats["camera_errors"] += 1
        return JSONResponse({"detail": "camera_failed", "why": "frame too large"}, status_code=502)

    _stats["on_request"] += 1
    print(f"[capture] {device_id} took a photo on request via {answered} ({len(raw)} bytes)", flush=True)
    try:
        reply = await _score(raw, device_id, sensor, job_id, "camera", received_at, t0)
    except HTTPException as exc:
        if exc.status_code == 400:
            # The camera sent something that is not a picture.
            return JSONResponse({"detail": "camera_failed", "why": exc.detail}, status_code=502)
        raise
    return JSONResponse({**reply, "camera": answered})


def _default_camera() -> str:
    """The camera heard from most recently, or the configured one."""
    with _cameras_lock:
        if _cameras:
            return max(_cameras.items(), key=lambda kv: kv[1].get("seen_at", ""))[0]
    return CAMERA_ID


async def _score(
    raw: bytes,
    device_id: str,
    sensor: str | None,
    job_id: str | None,
    job_kind: str | None,
    received_at: str,
    t0: float,
) -> dict:
    """Decode, run the model, store the frame, queue the record. Shared by a
    frame the camera posted and a photo taken on request, so both reach the
    server exactly the same way."""
    if not raw:
        _stats["failed"] += 1
        raise HTTPException(status_code=400, detail="Empty image body")

    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        _stats["failed"] += 1
        raise HTTPException(status_code=400, detail="Could not decode image as JPEG")

    sensors = parse_sensors(sensor, device_id)

    try:
        model = await run_in_threadpool(load_model)
    except Exception as exc:
        _stats["failed"] += 1
        # 503 so the node retries later instead of discarding the frame.
        raise HTTPException(status_code=503, detail=f"Model unavailable: {exc}") from exc

    try:
        # Off the event loop: /health and the next frame stay responsive while
        # the network runs.
        result = sanitise_result(await run_in_threadpool(model.predict, frame, sensors))
    except Exception as exc:
        _stats["failed"] += 1
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
    unreadable = result.pop("unreadable")

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    capture_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"

    image_path = None
    if KEEP_CAPTURES:
        image_path = os.path.join(CAPTURE_DIR, f"{capture_id}.jpg")
        with open(image_path, "wb") as fh:
            fh.write(raw)

    record = {
        "capture_id": capture_id,
        "site_id": SITE_ID,
        "device_id": device_id,
        "received_at": received_at,
        "latency_ms": latency_ms,
        "image_bytes": len(raw),
        "image_width": int(frame.shape[1]),
        "image_height": int(frame.shape[0]),
        "image_path": image_path,
        "sensors": sensors,
        **result,
    }
    if job_id:
        record["job_id"] = job_id
    if job_kind:
        # Tells the uploader the server has no copy of this photo yet, unlike
        # a phone scan, so the frame has to go up with the reading.
        record["job_kind"] = job_kind

    # An unreadable frame still carries the sensor readings, and those matter
    # at night when every frame is dark, so it goes upstream without a leaf
    # score. A job the farmer is waiting on that could not be read is not a
    # reading at all: agent.py tells the server, and the farmer is asked to
    # retake it.
    queue_id = None
    if not unreadable or (sensors and not job_id):
        queue_id = uploader.enqueue(record)

    _stats["unreadable" if unreadable else "analyzed"] += 1
    _stats["last_result"] = {
        "capture_id": capture_id,
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "label": result["label"],
        "unreadable": unreadable,
        "at": received_at,
    }
    if unreadable:
        verdict = f"unreadable ({unreadable})"
    else:
        verdict = (f"{result['risk_level']} ({result['risk_score']}) "
                   f"{result['label']} {result['confidence']}")
    sent = f"queued #{queue_id}" if queue_id else "not sent upstream"
    print(
        f"[analyze] {device_id}{' job ' + job_id if job_id else ''} -> {verdict} "
        f"in {latency_ms} ms, {sent}",
        flush=True,
    )

    # Keep the reply small: the ESP32 parses it on every cycle. An unreadable
    # frame answers with null score and level; the firmware prints -1/unknown
    # and skips the blink.
    return {
        "capture_id": capture_id,
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "label": result["label"],
        "confidence": result["confidence"],
        "model_version": result["model_version"],
        "latency_ms": latency_ms,
        "unreadable": unreadable,
        "queued": queue_id is not None,
    }


@app.get("/captures/{capture_id}", dependencies=[Depends(require_node_key)])
def get_capture(capture_id: str) -> FileResponse:
    """Serve a stored frame, so you can eyeball what the node actually saw:

        curl -H "X-Node-Key: $LEAFNODE_NODE_KEY" http://<pi>:8000/captures/<id> -o leaf.jpg
    """
    if not _SAFE_ID.match(capture_id):
        raise HTTPException(status_code=400, detail="Bad capture id")
    path = os.path.join(CAPTURE_DIR, f"{capture_id}.jpg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No such capture")
    return FileResponse(path, media_type="image/jpeg")

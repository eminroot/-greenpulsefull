"""
GreenPulse Edge Bridge (FastAPI)
----------------------------------------------------------------
Exposes the existing Layer 1-6 pipeline over HTTP so the GreenPulse mobile app
can run a real YOLOv11n-Seg + HSV leaf analysis on a paired edge device
(Raspberry Pi / Jetson) over the local network. No internet required — the
phone and the edge node only need to be on the same Wi-Fi/LAN.

The response body is the same JSON schema the app already understands (the
on-device TypeScript port produces an identical shape), so the app does not
care whether the analysis ran on the phone or on the edge node.

Run:
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8000

Then in the app's Settings, set the edge device URL to:
    http://<edge-device-lan-ip>:8000
"""

import io
import os

import numpy as np
import cv2
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pipeline import GreenPulsePipeline
from hal import SensorReading

WEIGHTS_PATH = os.environ.get("GREENPULSE_WEIGHTS", "models/yolo11n-seg.pt")
DEVICE = os.environ.get("GREENPULSE_DEVICE", "cpu")

app = FastAPI(title="GreenPulse Edge Bridge", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy singleton so the YOLO weights load once, on first request.
_pipeline: GreenPulsePipeline | None = None


def get_pipeline() -> GreenPulsePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = GreenPulsePipeline(weights_path=WEIGHTS_PATH, device=DEVICE)
    return _pipeline


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "greenpulse-edge",
        "weights": WEIGHTS_PATH,
        "device": DEVICE,
        "model_loaded": _pipeline is not None,
    }


@app.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    scenario: str = Form("normal"),
    sensor: str | None = Form(None),
) -> dict:
    raw = await image.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    try:
        pipeline = get_pipeline()
    except Exception as exc:  # noqa: BLE001 — surface model-load issues to the app
        raise HTTPException(status_code=503, detail=f"Model load failed: {exc}") from exc

    kwargs: dict = {}
    if sensor:
        import json

        try:
            payload = json.loads(sensor)
            kwargs["sensor_reading"] = SensorReading(
                soil_moisture=float(payload["soil_moisture"]),
                temperature=float(payload["temperature"]),
                humidity=float(payload["humidity"]),
                light=float(payload["light"]),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=f"Bad sensor payload: {exc}") from exc
    else:
        kwargs["sensor_mode"] = "simulated"
        kwargs["scenario"] = scenario

    result = pipeline.run(frame, **kwargs)
    # Tag where the analysis ran so the app can show a real-vision badge.
    result.setdefault("_meta", {})["vision_source"] = "edge-device"
    return result

"""Fills a server with a plausible history, for looking at the panel.

This is a development convenience, not part of the product: it talks to the
normal ingest endpoint exactly as a Raspberry Pi would, so everything it creates
is a real record that went through the real scoring. Nothing here bypasses the
server or fabricates a stored value.

    python tools/seed_demo.py [http://127.0.0.1:8000] [email] [password]
"""

from __future__ import annotations

import math
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010101006000600000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc40014000100000000000000000000000000000009ffc40014100100000000000000000000000000000000ffda0008010100003f0029ffd9"
)

HOURS = 36
STEP_MINUTES = 90


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    email = sys.argv[2] if len(sys.argv) > 2 else f"demo-{int(time.time())}@example.com"
    password = sys.argv[3] if len(sys.argv) > 3 else "greenhouse1"

    with httpx.Client(base_url=base, timeout=30) as http:
        res = http.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "name": "Demo Grower"},
        )
        if res.status_code == 409:
            res = http.post("/api/v1/auth/login", json={"email": email, "password": password})
        res.raise_for_status()

        access = res.json()["access_token"]
        auth = {"Authorization": f"Bearer {access}"}

        site = http.get("/api/v1/sites", headers=auth).json()[0]
        paired = http.post(
            f"/api/v1/sites/{site['id']}/devices",
            json={"name": "Greenhouse Pi", "kind": "pi"},
            headers=auth,
        )
        paired.raise_for_status()
        node = {"Authorization": f"Bearer {paired.json()['token']}"}

        print(f"account : {email} / {password}")
        print(f"site    : {site['name']}")

        now = datetime.now(timezone.utc)
        steps = int(HOURS * 60 / STEP_MINUTES)
        stored = 0

        for i in range(steps):
            at = now - timedelta(minutes=STEP_MINUTES * (steps - i - 1))
            phase = i / steps

            # A greenhouse drying out through the afternoon and recovering after
            # the system irrigates. Shaped so the history has something to show.
            soil = 62 - 58 * math.sin(phase * math.pi) ** 2
            temp = 21 + 9 * math.sin(phase * math.pi * 2) ** 2
            humidity = 66 - 14 * math.sin(phase * math.pi) ** 2
            risk = 8 + 52 * math.sin(phase * math.pi) ** 2

            body = {
                "capture_id": f"demo-{int(at.timestamp())}",
                "site_id": site["slug"],
                "device_id": "leafnode-01",
                "received_at": at.isoformat(),
                "latency_ms": round(150 + 60 * math.sin(i), 1),
                "sensors": {
                    "soil_moisture": round(soil, 1),
                    "temperature": round(temp, 1),
                    "humidity": round(humidity, 1),
                },
                "risk_score": round(risk, 1),
                "risk_level": "low" if risk < 25 else "medium" if risk < 50 else "high",
                "label": "healthy" if risk < 25 else "early_blight",
                "confidence": round(0.72 + 0.2 * (1 - abs(0.5 - phase) * 2), 2),
                "model_version": "leafnode-placeholder-1",
            }

            up = http.post("/api/v1/ingest/capture", json=body, headers=node)
            up.raise_for_status()
            stored += 1

            # A photo on some of them, so the gallery has content.
            if i % 3 == 0:
                http.post(
                    f"/api/v1/ingest/capture/{body['capture_id']}/image",
                    files={"image": ("leaf.jpg", TINY_JPEG, "image/jpeg")},
                    headers=node,
                ).raise_for_status()

        sus = http.get(f"/api/v1/sites/{site['id']}/sustainability", headers=auth).json()
        print(f"stored  : {stored} readings")
        print(f"actions : {sus['autonomous_actions']} autonomous, {sus['alerts']} alerts")
        print()
        print("Sign in to the panel with the account above.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

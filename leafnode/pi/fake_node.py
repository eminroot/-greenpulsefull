"""
Stand in for the ESP32 so you can test the Pi half with no hardware attached.

Posts an image to /analyze exactly the way the firmware does: multipart body,
same field names, same optional sensor blob.

    python fake_node.py                      # generates a synthetic leaf
    python fake_node.py path/to/photo.jpg    # uses a real photo
"""

import json
import os
import sys

import cv2
import numpy as np
import requests

URL = os.environ.get("LEAFNODE_TEST_URL", "http://127.0.0.1:8000/analyze")
# Same key the ESP32 carries. Read from the environment, so on the Pi:
#   set -a && . ./.env && set +a && python fake_node.py
NODE_KEY = os.environ.get("LEAFNODE_NODE_KEY", "")


def synthetic_leaf() -> bytes:
    """A green blob with a brown patch, enough to exercise the whole path."""
    img = np.full((600, 800, 3), (40, 30, 25), dtype=np.uint8)
    cv2.ellipse(img, (400, 300), (260, 160), 20, 0, 360, (60, 170, 60), -1)
    cv2.ellipse(img, (330, 260), (70, 45), -10, 0, 360, (40, 110, 165), -1)
    ok, buf = cv2.imencode(".jpg", img)
    if not ok:
        raise RuntimeError("could not encode the synthetic frame")
    return buf.tobytes()


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "rb") as fh:
            jpeg = fh.read()
        source = sys.argv[1]
    else:
        jpeg = synthetic_leaf()
        source = "synthetic"

    sensors = {"temperature": 29.4, "humidity": 48.0, "soil_moisture": 26.5}

    print(f"POST {URL}  source={source}  {len(jpeg)} bytes")
    resp = requests.post(
        URL,
        files={"image": ("leaf.jpg", jpeg, "image/jpeg")},
        data={"device_id": "fake-node", "sensor": json.dumps(sensors)},
        headers={"X-Node-Key": NODE_KEY},
        timeout=60,
    )
    print(f"HTTP {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))


if __name__ == "__main__":
    main()

"""
How fast is the leaf model on this machine, and how much memory does it take?

Run it on the Pi after setup.sh, with the service stopped or idle:

    cd ~/leafnode/pi
    .venv/bin/python bench.py                     # synthetic frames
    .venv/bin/python bench.py photo1.jpg ...      # your own leaf photos
    .venv/bin/python bench.py --json > bench.json # for the ML team's report

It times each stage the service runs for a frame (JPEG decode, preprocessing
and the quality check, the network) at the two sizes that actually arrive: an
ESP32-CAM frame (800x600) and a phone photo after the app compresses it.
The ML team listed Raspberry Pi runtime as not yet measured; this measures it.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(50_000_000))

import cv2
import numpy as np


def rss_mb() -> float | None:
    try:
        with open("/proc/self/status", encoding="ascii") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    try:
        import psutil

        return round(psutil.Process().memory_info().rss / 2**20, 1)
    except ImportError:
        return None


def cpu_temp_c() -> float | None:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", encoding="ascii") as fh:
            return round(int(fh.read().strip()) / 1000, 1)
    except (OSError, ValueError):
        return None


def board() -> str:
    try:
        with open("/proc/device-tree/model", encoding="ascii", errors="ignore") as fh:
            return fh.read().strip("\x00\n ")
    except OSError:
        return platform.machine()


def synthetic(width: int, height: int) -> bytes:
    """A leaf-ish frame; timing does not depend on what the picture shows."""
    rng = np.random.default_rng(width)
    img = np.clip(rng.normal(70, 25, (height, width, 3)), 0, 255).astype(np.uint8)
    cv2.ellipse(img, (width // 2, height // 2), (width // 3, height // 4), 20, 0, 360,
                (60, 160, 70), -1)
    cv2.circle(img, (width // 2 - width // 10, height // 2), width // 20, (40, 90, 140), -1)
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()


def pct(values: list[float], q: float) -> float:
    values = sorted(values)
    return round(values[min(len(values) - 1, int(q * len(values)))], 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="*", help="JPEG files to time instead of synthetic frames")
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from leaf_classifier import from_env, look_at, preprocess, unreadable_reason

    base_rss = rss_mb()
    t0 = time.perf_counter()
    model = from_env()
    load_ms = (time.perf_counter() - t0) * 1000
    model.predict(np.zeros((224, 224, 3), np.uint8), None)  # warm up
    loaded_rss = rss_mb()

    if args.images:
        inputs = {os.path.basename(p): open(p, "rb").read() for p in args.images}
    else:
        inputs = {"esp32_800x600": synthetic(800, 600), "phone_1280x960": synthetic(1280, 960)}

    report = {
        "board": board(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "onnxruntime": __import__("onnxruntime").__version__,
        "model": model.version,
        "crop": model.crop,
        "threads": int(os.environ.get("LEAFNODE_THREADS", "0") or 0) or os.cpu_count(),
        "load_ms": round(load_ms, 1),
        "rss_mb": {"before_model": base_rss, "model_loaded": loaded_rss},
        "cpu_temp_c_start": cpu_temp_c(),
        "frames": {},
    }

    for name, jpeg in inputs.items():
        stages: dict[str, list[float]] = {"decode": [], "prepare": [], "network": [], "total": []}
        for _ in range(args.runs):
            t0 = time.perf_counter()
            frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            t1 = time.perf_counter()
            crop = preprocess(frame, model.size)
            unreadable_reason(frame.shape[1], frame.shape[0], look_at(crop))
            t2 = time.perf_counter()
            model.probabilities(crop)
            t3 = time.perf_counter()
            for key, value in (("decode", t1 - t0), ("prepare", t2 - t1),
                               ("network", t3 - t2), ("total", t3 - t0)):
                stages[key].append(value * 1000)
        report["frames"][name] = {
            "size": f"{frame.shape[1]}x{frame.shape[0]}",
            **{k: {"median_ms": round(statistics.median(v), 1), "p95_ms": pct(v, 0.95)}
               for k, v in stages.items()},
        }

    report["rss_mb"]["peak_after_runs"] = rss_mb()
    report["cpu_temp_c_end"] = cpu_temp_c()

    if args.json:
        json.dump(report, sys.stdout, indent=2)
        print()
        return 0

    print(f"{report['board']}  python {report['python']}  onnxruntime {report['onnxruntime']}")
    print(f"model {model.version} ({model.crop}) loaded in {report['load_ms']:.0f} ms, "
          f"{report['threads']} threads")
    if loaded_rss is None:
        print("memory: not measurable here (no /proc and no psutil)")
    else:
        print(f"memory: {base_rss} MB before the model, {loaded_rss} MB loaded, "
              f"{report['rss_mb']['peak_after_runs']} MB after {args.runs} runs per size")
    for name, row in report["frames"].items():
        print(f"\n{name} ({row['size']}), {args.runs} runs, median / p95 ms")
        for stage in ("decode", "prepare", "network", "total"):
            print(f"  {stage:<8} {row[stage]['median_ms']:>7} {row[stage]['p95_ms']:>7}")
    if report["cpu_temp_c_start"] is not None:
        print(f"\nCPU {report['cpu_temp_c_start']} C before, {report['cpu_temp_c_end']} C after")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Does the Pi read a leaf exactly the way the ML team measured it?

The Pi runs the models on onnxruntime with its own preprocessing
(pi/leaf_classifier.py). The accuracy the team reported was measured through
ultralytics. This runs both on the same files and compares:

  1. validation accuracy through the Pi's code, which must equal the team's
     own validation figure (tomato 2711/2725, pepper 371/371)
  2. class probabilities, Pi code vs ultralytics, image by image
  3. the same comparison on non-square and large copies of those images, since
     the ESP32 (800x600) and phones (4:3, 12 MP) never send a 256x256 square
  4. the unreadable-frame gate: no validation leaf may be refused, and frames
     with no leaf in them must be

Needs ultralytics, so it runs on a dev machine, not the Pi:

    python tools/check_parity.py --ml "<path to the GreenPulse ML package>"

Validation images only. The team's test set is spent and stays untouched.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np

PI_DIR = Path(__file__).resolve().parent.parent / "pi"
sys.path.insert(0, str(PI_DIR))

from leaf_classifier import (  # noqa: E402
    MIN_LEAF_SHARE,
    LeafDiseaseClassifier,
    WEIGHTS_DIR,
    load_manifest,
    look_at,
    preprocess,
    unreadable_reason,
)

VAL_DIRS = {
    "tomato": "datasets/processed/tomato_hybrid_v1/val",
    "pepper": "datasets/processed/pepper_cls_leafgroup_v1/val",
}
EXPECTED_CORRECT = {"tomato": (2711, 2725), "pepper": (371, 371)}
MAX_PROB_DIFF = 1e-4  # the team's own ONNX parity tolerance

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'  ok  ' if ok else '  FAIL'} {label}{'  -> ' + detail if detail else ''}", flush=True)
    if not ok:
        failures.append(label)


def decode(path: Path) -> np.ndarray:
    frame = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise SystemExit(f"cannot decode {path}")
    return frame


def variants(frame: np.ndarray) -> dict[str, np.ndarray]:
    """Shapes the real cameras produce, built from a validation leaf."""
    h, w = frame.shape[:2]
    border = cv2.copyMakeBorder(frame, 0, 0, w // 6, w // 6, cv2.BORDER_REFLECT)
    return {
        "esp32_800x600": cv2.resize(border, (800, 600), interpolation=cv2.INTER_CUBIC),
        "phone_4032x3024": cv2.resize(border, (4032, 3024), interpolation=cv2.INTER_CUBIC),
        "portrait_480x640": cv2.resize(cv2.rotate(border, cv2.ROTATE_90_CLOCKWISE), (480, 640)),
        "odd_301x223": cv2.resize(border, (301, 223), interpolation=cv2.INTER_AREA),
    }


def non_leaves() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(7)
    wall = np.clip(rng.normal(150, 12, (600, 800, 3)), 0, 255).astype(np.uint8)
    night = np.clip(rng.normal(5, 3, (600, 800, 3)), 0, 255).astype(np.uint8)
    dusk = np.clip(rng.normal(22, 8, (600, 800, 3)), 0, 255).astype(np.uint8)
    sky = np.zeros((600, 800, 3), np.uint8)
    sky[:] = (235, 190, 120)  # BGR light blue
    return {
        "black": np.zeros((600, 800, 3), np.uint8),
        "white": np.full((600, 800, 3), 255, np.uint8),
        "night_noise": night,
        "dusk_noise": dusk,
        "grey_wall": wall,
        "blue_sky": sky,
        "tiny_leaf_crop": np.zeros((64, 64, 3), np.uint8),
    }


def run_crop(crop: str, ml_dir: Path, per_class: int, yolo_cls) -> None:
    manifest = load_manifest()[crop]
    names = [c["name"] for c in manifest["classes"]]
    model = LeafDiseaseClassifier(crop)
    val_dir = ml_dir / VAL_DIRS[crop]
    if not val_dir.is_dir():
        check(f"{crop}: validation images found", False, str(val_dir))
        return

    images = sorted((p, names.index(p.parent.name)) for p in val_dir.glob("*/*") if p.is_file())
    print(f"\n== {crop}: {model.version}, {len(images)} validation images")

    # 1 + 4a. Every validation image through the Pi's code.
    correct, refused, shares, t_total = 0, [], [], 0.0
    for path, truth in images:
        frame = decode(path)
        t0 = time.perf_counter()
        result = model.predict(frame, None)
        t_total += time.perf_counter() - t0
        quality = result.extra["diagnosis"]["quality"]
        shares.append(quality["leaf_share"])
        if result.unreadable:
            refused.append(f"{path.name}:{result.unreadable}")
            continue
        correct += result.label == manifest["classes"][truth]["code"]
    want, total = EXPECTED_CORRECT[crop]
    check(f"{crop}: validation accuracy through the Pi code matches the team's",
          (correct, len(images)) == (want, total),
          f"{correct}/{len(images)} (team: {want}/{total}), {t_total / len(images) * 1000:.1f} ms/image")
    check(f"{crop}: no validation leaf is refused as unreadable", not refused,
          f"{len(refused)} refused {refused[:3]}; lowest leaf share {min(shares):.3f} "
          f"(cut-off {MIN_LEAF_SHARE})")

    # 2. Probabilities vs ultralytics, a spread of images per class.
    yolo = yolo_cls(str(WEIGHTS_DIR / manifest["file"]), task="classify")
    by_class: dict[int, list[Path]] = {}
    for path, truth in images:
        by_class.setdefault(truth, []).append(path)
    sample = [p for paths in by_class.values() for p in paths[:: max(1, len(paths) // per_class)][:per_class]]

    worst, agree = 0.0, 0
    for path in sample:
        ours = model.probabilities(preprocess(decode(path), model.size))
        theirs = yolo.predict(source=str(path), imgsz=model.size, device="cpu", verbose=False)[0]
        theirs = theirs.probs.data.cpu().numpy()
        worst = max(worst, float(np.abs(ours - theirs).max()))
        agree += int(ours.argmax() == theirs.argmax())
    check(f"{crop}: same probabilities as ultralytics on {len(sample)} images",
          agree == len(sample) and worst < MAX_PROB_DIFF,
          f"top-1 agree {agree}/{len(sample)}, max |dp| {worst:.2e}")

    # 3. Camera-shaped inputs, written to disk so ultralytics reads them itself.
    worst, agree, count = 0.0, 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, path in enumerate(sample[:: max(1, len(sample) // 12)]):
            for name, img in variants(decode(path)).items():
                file = Path(tmp) / f"{i}_{name}.jpg"
                cv2.imwrite(str(file), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
                ours = model.probabilities(preprocess(decode(file), model.size))
                theirs = yolo.predict(source=str(file), imgsz=model.size, device="cpu", verbose=False)[0]
                theirs = theirs.probs.data.cpu().numpy()
                worst = max(worst, float(np.abs(ours - theirs).max()))
                agree += int(ours.argmax() == theirs.argmax())
                count += 1
    check(f"{crop}: same probabilities on ESP32, phone and odd-sized frames",
          agree == count and worst < MAX_PROB_DIFF,
          f"top-1 agree {agree}/{count}, max |dp| {worst:.2e}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ml", required=True, type=Path, help="the ML team's GreenPulse folder")
    parser.add_argument("--per-class", type=int, default=25)
    parser.add_argument("--crop", choices=sorted(VAL_DIRS), action="append")
    args = parser.parse_args()

    from ultralytics import YOLO

    for crop in args.crop or sorted(VAL_DIRS):
        run_crop(crop, args.ml.resolve(), args.per_class, YOLO)

    # 4b. Frames with nothing to read must be refused, not diagnosed.
    print("\n== frames with no leaf")
    for name, frame in non_leaves().items():
        crop_img = preprocess(frame, 224)
        reason = unreadable_reason(frame.shape[1], frame.shape[0], look_at(crop_img))
        check(f"refused: {name}", reason is not None, reason or "diagnosed anyway")

    print(f"\n{'all checks passed' if not failures else f'{len(failures)} failed: {failures}'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

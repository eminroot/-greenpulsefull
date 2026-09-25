"""
The GreenPulse leaf disease classifier, as trained by the ML team.

YOLO11n classification networks exported to ONNX, one per crop, listed in
weights/models.json:

    tomato   10 classes, 9 diseases + healthy     tomato_clean_v1
    pepper    2 classes, bacterial spot + healthy pepper_transfer_v1

It runs on onnxruntime, numpy and Pillow only. torch and ultralytics would add
about a gigabyte and several seconds of import time to the Pi for a network
that needs half a GFLOP.

Preprocessing reproduces what ultralytics 8.4 does at predict time, step for
step, because the accuracy the ML team measured is only valid for inputs
prepared the same way:

    shortest side to 224 with Pillow bilinear (antialiased), centre crop
    224x224, BGR to RGB, divide by 255, no mean or std

tools/check_parity.py compares this file against ultralytics on the
validation images. Run it again whenever a new model arrives.

Before the network sees a frame, it has to look like something the network can
read. A frame that is black, blown out, tiny, or has no leaf in the middle
comes back as "unreadable" with a reason, rather than as a confident disease
the network invented for a picture of the wall.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

from model import RiskResult, band_for

WEIGHTS_DIR = Path(__file__).resolve().parent / "weights"

# From the ML team's image_quality.py: below this the image is refused.
MIN_SIDE = 96
# Also theirs: only a frame that is almost entirely black or white is refused
# on exposure alone. Deliberately loose, their thresholds are unvalidated.
DARK_MEAN, DARK_SHARE = 12.0, 0.98
BRIGHT_MEAN, BRIGHT_SHARE = 243.0, 0.98
# Share of the centre crop that has to look like leaf tissue (green, yellow or
# brown, reasonably saturated and lit). Across the 3,096 validation images the
# lowest is 0.059 (a spider-mite leaf) and the median 0.35; a blank wall, sky
# or night frame scores 0.0. So 0.02 refuses nothing real. A dim frame that fails this is reported as too dark,
# since that is the likely cause and the fix is different.
MIN_LEAF_SHARE = 0.02
DIM_MEAN = 40.0


class ModelIntegrityError(RuntimeError):
    pass


def load_manifest(weights_dir: Path = WEIGHTS_DIR) -> dict:
    with open(weights_dir / "models.json", encoding="utf-8") as fh:
        return json.load(fh)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preprocess(frame_bgr: np.ndarray, size: int) -> np.ndarray:
    """A decoded BGR frame to the size x size RGB uint8 crop the network sees.

    Mirrors torchvision Resize(size) + CenterCrop(size) on a PIL image, which is
    what ultralytics' classify_transforms builds.
    """
    from PIL import Image

    h, w = frame_bgr.shape[:2]
    if w <= h:
        new_w, new_h = size, int(size * h / w)
    else:
        new_w, new_h = int(size * w / h), size

    # Pillow treats the array as RGB; resizing and cropping act on each channel
    # alone, so the order is fixed afterwards, exactly as ultralytics does.
    img = Image.fromarray(np.ascontiguousarray(frame_bgr))
    if (new_w, new_h) != (w, h):
        img = img.resize((new_w, new_h), Image.BILINEAR)
    top = int(round((new_h - size) / 2.0))
    left = int(round((new_w - size) / 2.0))
    img = img.crop((left, top, left + size, top + size))
    return np.ascontiguousarray(np.asarray(img)[..., ::-1])


def to_tensor(crop_rgb: np.ndarray) -> np.ndarray:
    return (crop_rgb.transpose(2, 0, 1)[None].astype(np.float32) / 255.0).copy()


def look_at(crop_rgb: np.ndarray) -> dict:
    """Cheap facts about the crop, used to refuse frames the network can't read."""
    import cv2

    gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2HSV)
    # Hue 8..85 on OpenCV's 0..179 scale runs from brown through yellow to
    # green. Same bands the placeholder model used.
    leaf = cv2.inRange(hsv, (8, 60, 40), (85, 255, 255))
    return {
        "brightness": round(float(gray.mean()), 1),
        "dark_share": round(float(np.mean(gray < 16)), 4),
        "bright_share": round(float(np.mean(gray > 239)), 4),
        "leaf_share": round(float(np.count_nonzero(leaf)) / leaf.size, 4),
        # Reported, not used: the ML team has no validated blur threshold yet.
        "sharpness": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1),
    }


def unreadable_reason(width: int, height: int, quality: dict) -> str | None:
    if min(width, height) < MIN_SIDE:
        return "too_small"
    if quality["brightness"] < DARK_MEAN and quality["dark_share"] > DARK_SHARE:
        return "too_dark"
    if quality["brightness"] > BRIGHT_MEAN and quality["bright_share"] > BRIGHT_SHARE:
        return "overexposed"
    if quality["leaf_share"] < MIN_LEAF_SHARE:
        return "too_dark" if quality["brightness"] < DIM_MEAN else "no_leaf"
    return None


class LeafDiseaseClassifier:
    def __init__(self, crop: str, weights_dir: Path = WEIGHTS_DIR, threads: int = 0):
        import onnxruntime as ort

        manifest = load_manifest(weights_dir)
        crops = sorted(k for k in manifest if not k.startswith("_"))
        if crop not in crops:
            raise ValueError(f"LEAFNODE_CROP={crop!r}, this Pi has models for: {', '.join(crops)}")
        entry = manifest[crop]

        path = weights_dir / entry["file"]
        if not path.is_file():
            raise FileNotFoundError(f"{path} is missing. Copy it from the ML team's release.")
        if _sha256(path) != entry["sha256"]:
            # A truncated copy or a different export would still load and run,
            # and quietly give different answers from the ones that were tested.
            raise ModelIntegrityError(f"{path.name} does not match the sha256 in models.json")

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.inter_op_num_threads = 1
        if threads > 0:
            opts.intra_op_num_threads = threads
        self._session = ort.InferenceSession(
            str(path), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self._input = self._session.get_inputs()[0].name

        self.crop = crop
        self.version = entry["version"]
        self.size = int(entry["input_size"])
        self.codes = [c["code"] for c in entry["classes"]]
        self.severity = np.array([float(c["severity"]) for c in entry["classes"]])

        # The export carries its own class list. If it disagrees with the
        # manifest, every label we report would be wrong, so refuse to start.
        names = self._session.get_modelmeta().custom_metadata_map.get("names")
        if names:
            exported = [v for _, v in sorted(ast.literal_eval(names).items())]
            if exported != [c["name"] for c in entry["classes"]]:
                raise ModelIntegrityError(
                    f"{path.name} classes {exported} do not match models.json"
                )
        out_shape = self._session.get_outputs()[0].shape
        if out_shape[-1] != len(self.codes):
            raise ModelIntegrityError(f"{path.name} outputs {out_shape}, expected {len(self.codes)} classes")

    def probabilities(self, crop_rgb: np.ndarray) -> np.ndarray:
        out = self._session.run(None, {self._input: to_tensor(crop_rgb)})[0][0].astype(np.float64)
        # Ultralytics exports classifiers with the softmax inside. Guard anyway:
        # a re-export without it would otherwise pass logits off as probabilities.
        if out.min() < 0 or abs(out.sum() - 1.0) > 1e-3:
            out = np.exp(out - out.max())
            out /= out.sum()
        return out

    def predict(self, frame: np.ndarray, sensors: dict | None) -> RiskResult:
        height, width = frame.shape[:2]
        crop = preprocess(frame, self.size)
        quality = look_at(crop)

        reason = unreadable_reason(width, height, quality)
        if reason:
            return RiskResult(
                risk_score=None,
                risk_level=None,
                label=reason,
                confidence=None,
                model_version=self.version,
                extra={"diagnosis": {
                    "status": "unreadable",
                    "reason": reason,
                    "crop": self.crop,
                    "model": self.version,
                    "quality": quality,
                }},
                unreadable=reason,
            )

        t0 = time.perf_counter()
        probs = self.probabilities(crop)
        network_ms = round((time.perf_counter() - t0) * 1000, 1)

        order = np.argsort(probs)[::-1]
        top = int(order[0])
        # Probability-weighted severity: a confident late blight scores near
        # 95, a leaf the network is torn about scores in between, a confident
        # healthy leaf scores near 0.
        score = round(float(probs @ self.severity), 1)

        return RiskResult(
            risk_score=score,
            risk_level=band_for(score),
            label=self.codes[top],
            confidence=round(float(probs[top]), 4),
            model_version=self.version,
            extra={"diagnosis": {
                "status": "ok",
                "crop": self.crop,
                "code": self.codes[top],
                "healthy": self.codes[top] == "healthy",
                "confidence": round(float(probs[top]), 4),
                "top": [
                    {"code": self.codes[int(i)], "p": round(float(probs[int(i)]), 4)}
                    for i in order[:3]
                ],
                "model": self.version,
                "network_ms": network_ms,
                "quality": quality,
            }},
        )


def from_env() -> LeafDiseaseClassifier:
    weights = os.environ.get("LEAFNODE_WEIGHTS_DIR", "").strip()
    return LeafDiseaseClassifier(
        crop=os.environ.get("LEAFNODE_CROP", "tomato").strip().lower(),
        weights_dir=Path(weights).resolve() if weights else WEIGHTS_DIR,
        threads=int(os.environ.get("LEAFNODE_THREADS", "0") or 0),
    )

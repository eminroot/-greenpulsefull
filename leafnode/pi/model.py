"""
The model seam.

Everything else in the Pi service (HTTP, image decoding, storage, upstream
upload, retries) is done and does not care what happens in here.

The contract, in one sentence: given a decoded BGR image and an optional dict
of sensor readings, return a RiskResult.

Two models are registered:
  greenpulse   the ML team's trained leaf disease classifier (leaf_classifier.py,
               weights in weights/), the default
  placeholder  a green versus brown pixel count, kept for testing the wiring;
               it is NOT a diagnosis

To plug in another one:
  1. write a class with a .predict(frame, sensors) -> RiskResult method
  2. register it in load_model() under a new name
  3. set LEAFNODE_MODEL=<that name> in the environment (see .env.example)

Nothing else changes. The ESP32 firmware does not change either.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Protocol

import numpy as np


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

RISK_BANDS = ("low", "medium", "high", "critical")


@dataclass
class RiskResult:
    """What every model must return."""

    risk_score: float | None   # 0..100, higher is worse; None only when unreadable
    risk_level: str | None     # one of RISK_BANDS; None only when unreadable
    label: str                 # the finding, e.g. "early_blight"
    confidence: float | None   # 0..1
    model_version: str         # whatever identifies the weights, goes into records
    extra: dict[str, Any] = field(default_factory=dict)   # anything else, passed through
    # Set when the frame could not be read at all (too dark, no leaf in view).
    # The model then gives no score rather than guessing one.
    unreadable: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def band_for(score: float) -> str:
    """Single place that decides where the band boundaries sit."""
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "critical"


class RiskModel(Protocol):
    """Structural type. Any object with this method is a valid model."""

    def predict(self, frame: np.ndarray, sensors: dict | None) -> RiskResult:
        ...


# ---------------------------------------------------------------------------
# Placeholder, for testing the wiring without the real model
# ---------------------------------------------------------------------------


class PlaceholderModel:
    """
    Not a model. A stand-in that was used to wire and demonstrate the whole
    chain (ESP32 -> Pi -> server) before the trained weights existed.

    It looks at how much of the frame is green versus brown/yellow and turns
    that into a number. That is a real measurement, but it is not a diagnosis:
    a brown table under the leaf will score as badly as a dying leaf. Treat
    every number it emits as a placeholder.
    """

    version = "placeholder-1"

    def predict(self, frame: np.ndarray, sensors: dict | None) -> RiskResult:
        import cv2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Healthy foliage sits roughly at hue 35..85 in OpenCV's 0..179 scale.
        healthy = cv2.inRange(hsv, (35, 60, 40), (85, 255, 255))
        # Chlorotic yellow through necrotic brown.
        stressed = cv2.inRange(hsv, (8, 60, 40), (34, 255, 255))

        healthy_px = int(np.count_nonzero(healthy))
        stressed_px = int(np.count_nonzero(stressed))
        plant_px = healthy_px + stressed_px

        if plant_px < (frame.shape[0] * frame.shape[1]) * 0.02:
            # Almost no plant material in view. Say so rather than inventing a score.
            return RiskResult(
                risk_score=None,
                risk_level=None,
                label="no_leaf",
                confidence=None,
                model_version=self.version,
                extra={"healthy_px": healthy_px, "stressed_px": stressed_px},
                unreadable="no_leaf",
            )

        damage_ratio = stressed_px / plant_px
        score = round(min(100.0, damage_ratio * 130.0), 1)

        return RiskResult(
            risk_score=score,
            risk_level=band_for(score),
            label="leaf_discolouration" if score >= 25 else "leaf_healthy",
            confidence=round(min(1.0, plant_px / (frame.shape[0] * frame.shape[1]) * 3), 2),
            model_version=self.version,
            extra={
                "damage_ratio": round(damage_ratio, 4),
                "healthy_px": healthy_px,
                "stressed_px": stressed_px,
                "placeholder": True,
            },
        )


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

_cached: RiskModel | None = None
_load_error: str | None = None
_load_lock = threading.Lock()


def _selected() -> str:
    return os.environ.get("LEAFNODE_MODEL", "greenpulse").strip().lower()


def load_model() -> RiskModel:
    """Lazy singleton. server.py warms it in the background at startup; the lock
    stops a request that arrives meanwhile from loading a second copy."""
    global _cached, _load_error
    if _cached is not None:
        return _cached

    with _load_lock:
        if _cached is not None:
            return _cached

        name = _selected()
        t0 = time.perf_counter()
        try:
            if name == "greenpulse":
                from leaf_classifier import from_env

                model: RiskModel = from_env()
            elif name == "placeholder":
                model = PlaceholderModel()
            else:
                raise ValueError(
                    f"Unknown LEAFNODE_MODEL={name!r}. "
                    "Use greenpulse, or add your class to load_model() in pi/model.py."
                )
        except Exception as exc:
            _load_error = f"{type(exc).__name__}: {exc}"
            raise

        _cached, _load_error = model, None
        print(f"[model] loaded {name} {getattr(model, 'version', '')} "
              f"in {(time.perf_counter() - t0) * 1000:.0f} ms", flush=True)
        return _cached


def model_info() -> dict:
    """Cheap description for /health, without forcing the weights to load."""
    return {
        "selected": _selected(),
        "crop": getattr(_cached, "crop", None) or os.environ.get("LEAFNODE_CROP", "tomato"),
        "loaded": _cached is not None,
        "version": getattr(_cached, "version", None),
        "error": _load_error,
    }

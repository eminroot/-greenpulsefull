"""Plant stress scoring.

Same constants, bands and weights as the reference engine in
greenpulse/greenpulse/gpss_engine.py. Two things differ, both because this now
runs on real hardware output rather than a simulation:

1.  The damage input is the model score the Raspberry Pi returns. Nothing in
    here looks at an image; the vision work stays entirely on the node.
2.  Any input may be missing, because a greenhouse may not have every probe
    wired, and a leaf photo taken at night or of an empty frame cannot be
    read. A missing input drops out of the weighted sum and the remaining
    weights are renormalised, so a site with no light sensor is not silently
    scored as if its light were perfect (or as if it were zero), and a dark
    frame is not scored as a healthy leaf.

The score runs 0..100 where higher means more stress.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


class NothingToScore(ValueError):
    """No leaf verdict and no sensor reading: there is no score to give."""


# Comfortable ranges for a typical greenhouse crop. Calibrate per species as
# real greenhouse data is collected.
IDEAL_SOIL_MOISTURE = (45.0, 70.0)  # %
IDEAL_TEMPERATURE = (18.0, 28.0)  # C
IDEAL_HUMIDITY = (50.0, 75.0)  # %
IDEAL_LIGHT = (400.0, 800.0)  # lux

WEIGHT_DAMAGE = 0.40
WEIGHT_WATER = 0.30
WEIGHT_THERMAL = 0.15
WEIGHT_LIGHT = 0.15

RISK_LOW = "Low"
RISK_MEDIUM = "Medium"
RISK_HIGH = "High"
RISK_CRITICAL = "Critical"


@dataclass
class GpssResult:
    gpss_score: int
    risk_level: str
    stress_type: str
    sub_scores: dict[str, float]
    signals: dict[str, bool]

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _deviation_score(
    value: float, low: float, high: float, hard_low: float, hard_high: float
) -> float:
    """0..100 stress contribution relative to the ideal band.

    0 means fully inside the band; it climbs toward 100 as the value approaches
    the physiological hard limit on either side.
    """
    if low <= value <= high:
        return 0.0
    if value < low:
        span = max(low - hard_low, 1e-6)
        return _clamp(100.0 * (low - value) / span, 0.0, 100.0)
    span = max(hard_high - high, 1e-6)
    return _clamp(100.0 * (value - high) / span, 0.0, 100.0)


def _round1(v: float) -> float:
    return round(v, 1)


def compute_gpss(
    *,
    damage_percentage: float | None,
    soil_moisture: float | None = None,
    temperature: float | None = None,
    humidity: float | None = None,
    light: float | None = None,
) -> GpssResult:
    """Fuse the model verdict with whatever environmental readings arrived."""

    damage_score = (
        _clamp(float(damage_percentage), 0.0, 100.0)
        if damage_percentage is not None
        else None
    )

    water_score = (
        _deviation_score(soil_moisture, *IDEAL_SOIL_MOISTURE, hard_low=0, hard_high=100)
        if soil_moisture is not None
        else None
    )
    thermal_score = (
        _deviation_score(temperature, *IDEAL_TEMPERATURE, hard_low=-5, hard_high=45)
        if temperature is not None
        else None
    )
    light_score = (
        _deviation_score(light, *IDEAL_LIGHT, hard_low=0, hard_high=1500)
        if light is not None
        else None
    )

    # Weighted mean over the inputs we actually have.
    parts: list[tuple[str, float, float]] = []
    if damage_score is not None:
        parts.append(("damage_score", damage_score, WEIGHT_DAMAGE))
    if water_score is not None:
        parts.append(("water_score", water_score, WEIGHT_WATER))
    if thermal_score is not None:
        parts.append(("thermal_score", thermal_score, WEIGHT_THERMAL))
    if light_score is not None:
        parts.append(("light_score", light_score, WEIGHT_LIGHT))

    if not parts:
        raise NothingToScore("no leaf verdict and no sensor reading")
    total_weight = sum(w for _, _, w in parts)
    raw = sum(value * weight for _, value, weight in parts) / total_weight
    gpss_score = int(round(_clamp(raw, 0.0, 100.0)))

    if gpss_score <= 25:
        risk_level = RISK_LOW
    elif gpss_score <= 50:
        risk_level = RISK_MEDIUM
    elif gpss_score <= 75:
        risk_level = RISK_HIGH
    else:
        risk_level = RISK_CRITICAL

    # Sub scores are reported for every input; a missing one reads as null in
    # the API rather than 0, so the app can label it honestly.
    sub_scores: dict[str, float] = {
        "damage_score": _round1(damage_score) if damage_score is not None else None,
        "water_score": _round1(water_score) if water_score is not None else None,
        "thermal_score": _round1(thermal_score) if thermal_score is not None else None,
        "light_score": _round1(light_score) if light_score is not None else None,
    }

    stress_map = {
        "damage_score": "Tissue Damage",
        "water_score": "Water Stress",
        "thermal_score": "Heat Stress",
        "light_score": "Light Stress",
    }
    # The weighted largest contributor names the stress type.
    dominant = max(parts, key=lambda p: p[1] * p[2])[0]
    stress_type = "Healthy" if gpss_score <= 15 else stress_map[dominant]

    signals = {
        "damage": damage_score is not None,
        "water": soil_moisture is not None,
        "thermal": temperature is not None,
        "light": light is not None,
        # Humidity is stored and shown but does not enter the score, matching
        # the reference engine.
        "humidity": humidity is not None,
    }

    return GpssResult(
        gpss_score=gpss_score,
        risk_level=risk_level,
        stress_type=stress_type,
        sub_scores=sub_scores,
        signals=signals,
    )


def damage_from_model(risk_score: float | None, risk_level: str | None) -> float | None:
    """Map the node model output onto the 0..100 damage input.

    The model already reports risk_score on a 0..100 scale where higher is
    worse, which is the same orientation, so it passes through. If a model ever
    reports only a band, fall back to the midpoint of that band. No verdict at
    all (the photo could not be read) means no damage input, not zero damage.
    """
    if risk_score is not None:
        return _clamp(float(risk_score), 0.0, 100.0)
    midpoints = {"low": 12.5, "medium": 37.5, "high": 62.5, "critical": 87.5}
    return midpoints.get((risk_level or "").lower())

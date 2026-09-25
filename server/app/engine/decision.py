"""Autonomous decision engine.

Port of greenpulse/greenpulse/decision_engine.py with the same thresholds. The
reason strings are written in English here; the app renders its own localised
wording from the decision code and score, so this text is for logs and the API,
not for the farmer's screen.

One addition: a disease the leaf model is confident about asks for a human
look even when the stress score is low. The score weights the leaf at 40%, so
a greenhouse with perfect sensor readings caps a certain late blight at 38,
under the action threshold, and the farmer would never hear of it. The
diagnosis never switches an actuator on; the ML team's model is cleared for
advice only, and no pump or fan fixes a blight.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .diagnosis import Diagnosis

# Above this GPSS value autonomous action begins.
ACTION_THRESHOLD = 50
# Above this value the farmer is notified as well.
ALERT_THRESHOLD = 76


@dataclass
class Decision:
    decision: str
    actuator: str
    notify_farmer: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def decide(
    gpss_score: int, stress_type: str, diagnosis: Diagnosis | None = None
) -> Decision:
    decision = _decide_from_score(gpss_score, stress_type)
    if diagnosis is None or not diagnosis.disease_found:
        return decision

    finding = (
        f"the leaf model reports {diagnosis.code} on {diagnosis.crop or 'the crop'} "
        f"({diagnosis.confidence:.0%} confidence)"
    )
    if decision.decision in ACTING_DECISIONS:
        # Keep acting on what the sensors show, and tell the farmer about the leaf.
        return Decision(
            decision.decision,
            decision.actuator,
            True,
            f"{decision.reason} Also, {finding}; inspect the plant.",
        )
    return Decision(
        "ALERT_AGRONOMIST",
        "NONE",
        True,
        f"{finding[0].upper()}{finding[1:]} (GPSS {gpss_score}); human inspection required.",
    )


def _decide_from_score(gpss_score: int, stress_type: str) -> Decision:
    if gpss_score < ACTION_THRESHOLD:
        return Decision(
            decision="MONITORING",
            actuator="NONE",
            notify_farmer=False,
            reason=(
                f"GPSS {gpss_score} is below the action threshold "
                f"({ACTION_THRESHOLD}); the plant is within a healthy range."
            ),
        )

    notify = gpss_score >= ALERT_THRESHOLD

    if stress_type == "Water Stress":
        return Decision(
            "IRRIGATION_ON",
            "WATER_PUMP",
            notify,
            f"Soil moisture deficit detected (GPSS {gpss_score}).",
        )
    if stress_type == "Heat Stress":
        return Decision(
            "VENTILATION_ON",
            "FAN",
            notify,
            f"Thermal stress detected (GPSS {gpss_score}).",
        )
    if stress_type == "Light Stress":
        return Decision(
            "SUPPLEMENTAL_LIGHT_ON",
            "GROW_LIGHT",
            notify,
            f"Light shortfall detected (GPSS {gpss_score}).",
        )
    if stress_type == "Tissue Damage":
        return Decision(
            "ALERT_AGRONOMIST",
            "NONE",
            True,
            f"Visible tissue damage detected (GPSS {gpss_score}); human inspection required.",
        )

    return Decision(
        "MONITORING",
        "NONE",
        notify,
        f"Elevated GPSS {gpss_score} with no single dominant cause.",
    )


ACTING_DECISIONS = {
    "IRRIGATION_ON",
    "VENTILATION_ON",
    "SUPPLEMENTAL_LIGHT_ON",
}

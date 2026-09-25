"""What the leaf model on the node concluded, read back out of the record.

The Pi's classifier (leafnode/pi/leaf_classifier.py) sends its full verdict in
the capture's `extra.diagnosis`: the crop, the disease code, the confidence and
the runners-up, or the reason a photo could not be read at all. It is stored
verbatim with the capture, so this module is the single place that parses it
back and decides what counts as a finding. Records from older nodes, or from
the placeholder model, simply have no diagnosis.

Codes are passed through, not translated: the app and the panel own the wording
in every language.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

# Below this, the top class is shown as a possibility, not a finding, and it
# does not alert the farmer. 0.65 is the ML team's own low-confidence line
# (configs/active_learning_policy_v1.json), which they mark as unvalidated.
MIN_CONFIDENCE = 0.65

_CODE = re.compile(r"^[a-z0-9_]{1,40}$")
STATUSES = {"ok", "unreadable"}


@dataclass
class Diagnosis:
    status: str  # "ok" or "unreadable"
    crop: str | None = None
    code: str | None = None
    confidence: float | None = None
    healthy: bool | None = None
    reason: str | None = None  # why an unreadable photo was refused
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    model: str | None = None

    @property
    def uncertain(self) -> bool:
        return self.status == "ok" and (self.confidence or 0.0) < MIN_CONFIDENCE

    @property
    def disease_found(self) -> bool:
        """A disease the model is reasonably sure of. This is what alerts."""
        return self.status == "ok" and self.healthy is False and not self.uncertain


def _code(value: Any) -> str | None:
    return value if isinstance(value, str) and _CODE.match(value) else None


def _prob(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return round(value, 4) if math.isfinite(value) and 0.0 <= value <= 1.0 else None


def parse_diagnosis(extra: dict[str, Any] | None) -> Diagnosis | None:
    """The node's verdict, or None if the record carries none we can trust.

    Checked field by field rather than trusted: this is node data, and a
    malformed value should cost the diagnosis card, not the whole reading.
    """
    raw = (extra or {}).get("diagnosis")
    if not isinstance(raw, dict) or raw.get("status") not in STATUSES:
        return None

    if raw["status"] == "unreadable":
        return Diagnosis(
            status="unreadable",
            crop=_code(raw.get("crop")),
            reason=_code(raw.get("reason")) or "unknown",
            model=str(raw.get("model"))[:120] if raw.get("model") else None,
        )

    code = _code(raw.get("code"))
    confidence = _prob(raw.get("confidence"))
    if code is None or confidence is None:
        return None

    alternatives = []
    for item in raw.get("top") or []:
        if not isinstance(item, dict):
            continue
        alt, p = _code(item.get("code")), _prob(item.get("p"))
        if alt and alt != code and p is not None:
            alternatives.append({"code": alt, "p": p})
    return Diagnosis(
        status="ok",
        crop=_code(raw.get("crop")),
        code=code,
        confidence=confidence,
        healthy=code == "healthy",
        alternatives=alternatives[:4],
        model=str(raw.get("model"))[:120] if raw.get("model") else None,
    )

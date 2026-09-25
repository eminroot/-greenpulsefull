"""Request and response bodies.

The ingest schema deliberately mirrors the record the LeafNode Pi service
already queues in pi/uploader.py, field for field, so the node needs a URL and
a token in its .env and nothing else.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# --- auth ------------------------------------------------------------------


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleIn(BaseModel):
    id_token: str


class RefreshIn(BaseModel):
    refresh_token: str


class UpdateMeIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)


class ChangePasswordIn(BaseModel):
    current_password: str | None = None
    new_password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str | None = None
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: UserOut


# --- sites and devices -----------------------------------------------------


class SiteCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=64)
    crop: str | None = Field(default=None, max_length=80)

    @field_validator("slug")
    @classmethod
    def _clean_slug(cls, v: str | None) -> str | None:
        return v.strip().lower() if v else v


class SiteOut(BaseModel):
    id: str
    name: str
    slug: str
    crop: str | None = None
    created_at: datetime
    device_count: int = 0
    online: bool = False
    last_capture_at: datetime | None = None


class DeviceCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["pi", "esp32", "other"] = "pi"


class DeviceOut(BaseModel):
    id: str
    site_id: str
    name: str
    kind: str
    token_prefix: str
    online: bool
    last_seen_at: datetime | None = None
    model_version: str | None = None
    created_at: datetime


class DeviceCreatedOut(DeviceOut):
    """Returned once, at pairing. The token is never retrievable again."""

    token: str
    setup: dict[str, str]


# --- readings and captures -------------------------------------------------


class ReadingOut(BaseModel):
    recorded_at: datetime
    soil_moisture: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    light: float | None = None
    soil_raw: int | None = None


class DiagnosisAlternativeOut(BaseModel):
    code: str
    p: float


class DiagnosisOut(BaseModel):
    """The leaf model's verdict. Codes, not words: each client translates them.

    status "ok": `code` is what the model sees (a disease, or "healthy") with
    its `confidence`; `uncertain` means below the line where it counts as a
    finding. status "unreadable": the photo could not be read, `reason` says
    why (too_dark, overexposed, no_leaf, too_small).
    """

    status: Literal["ok", "unreadable"]
    crop: str | None = None
    code: str | None = None
    confidence: float | None = None
    healthy: bool | None = None
    uncertain: bool = False
    disease_found: bool = False
    reason: str | None = None
    alternatives: list[DiagnosisAlternativeOut] = Field(default_factory=list)
    model: str | None = None


class CaptureOut(BaseModel):
    id: str
    site_id: str
    node_capture_id: str
    captured_at: datetime
    received_at: datetime
    source: str

    # model output, straight from the node; score and level are null when the
    # photo could not be read
    risk_score: float | None = None
    risk_level: str | None = None
    label: str | None = None
    confidence: float | None = None
    model_version: str | None = None
    inference_ms: float | None = None
    diagnosis: DiagnosisOut | None = None

    # fused verdict
    gpss_score: int
    gpss_risk_level: str
    stress_type: str
    sub_scores: dict[str, float | None]
    signals: dict[str, bool]
    decision: str
    actuator: str
    notify_farmer: bool
    decision_reason: str

    reading: ReadingOut | None = None
    image_url: str | None = None
    image_width: int | None = None
    image_height: int | None = None


class DeviceStatusOut(BaseModel):
    id: str
    name: str
    online: bool
    last_seen_at: datetime | None = None
    model_version: str | None = None


class LiveOut(BaseModel):
    """What the dashboard renders. Every field can be null: before the first
    node report there is genuinely nothing to show, and the app says so rather
    than inventing a number."""

    site: SiteOut
    capture: CaptureOut | None = None
    # Only when the newest capture has no leaf verdict (a dark or empty frame):
    # the most recent one that did.
    last_leaf_capture: CaptureOut | None = None
    reading: ReadingOut | None = None
    devices: list[DeviceStatusOut] = Field(default_factory=list)
    online: bool = False
    stale: bool = False
    seconds_since_reading: float | None = None
    server_time: datetime


class SeriesPoint(BaseModel):
    t: datetime
    v: float | None = None


class SeriesOut(BaseModel):
    metric: str
    points: list[SeriesPoint]


class ScorePreviewIn(BaseModel):
    """A what-if: what would the system do with these numbers?

    Used by the panel's digital twin so it predicts the real engine instead of
    keeping its own copy of the scoring, which would drift.
    """

    damage_percentage: float = Field(default=0, ge=0, le=100)
    soil_moisture: float | None = Field(default=None, ge=0, le=100)
    temperature: float | None = Field(default=None, ge=-30, le=80)
    humidity: float | None = Field(default=None, ge=0, le=100)
    light: float | None = Field(default=None, ge=0, le=200000)


class ScorePreviewOut(BaseModel):
    gpss_score: int
    risk_level: str
    stress_type: str
    sub_scores: dict[str, float | None]
    signals: dict[str, bool]
    decision: str
    actuator: str
    notify_farmer: bool
    decision_reason: str


class SustainabilityOut(BaseModel):
    irrigation_events: int
    ventilation_events: int
    light_events: int
    autonomous_actions: int
    alerts: int
    captures: int
    water_saved_pct: int
    energy_saved_pct: int
    cost_reduction: int
    co2_kg: int
    water_liters: int
    yield_protected_pct: int
    disease_risk_pct: int
    manual_checks: int
    labor_hours: int
    fertilizer_saved_pct: int
    since: datetime | None = None


# --- ingest (Raspberry Pi to server) ---------------------------------------


class SensorPayload(BaseModel):
    """Whatever the ESP32 wired up. Every field optional on purpose."""

    model_config = ConfigDict(extra="allow")

    soil_moisture: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    light: float | None = None
    soil_raw: int | None = None


class IngestCaptureIn(BaseModel):
    """The record pi/uploader.py sends. Unknown keys are kept in extra."""

    model_config = ConfigDict(extra="allow")

    # Constrained because it becomes part of a filename on disk. Anything
    # outside this set is refused rather than sanitised, so a surprising id from
    # a node is a visible error.
    capture_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    site_id: str | None = Field(default=None, max_length=80)
    # Stored in an 80 character column. Postgres refuses a longer value with a
    # 500, which a node's retry queue would redeliver forever.
    device_id: str | None = Field(default=None, max_length=80)
    received_at: datetime | None = None
    latency_ms: float | None = None

    image_bytes: int | None = None
    image_width: int | None = None
    image_height: int | None = None
    image_path: str | None = None
    image_b64: str | None = None  # optional single request image delivery

    sensors: SensorPayload | None = None

    risk_score: float | None = Field(default=None, ge=0, le=100)
    risk_level: str | None = Field(default=None, max_length=16)
    label: str | None = Field(default=None, max_length=120)
    confidence: float | None = Field(default=None, ge=0, le=1)
    model_version: str | None = Field(default=None, max_length=120)
    # Passed straight through to storage, so it is bounded here.
    extra: dict[str, Any] | None = None

    @field_validator("extra")
    @classmethod
    def _bound_extra(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None and len(json.dumps(v, default=str)) > 8192:
            raise ValueError("extra is too large")
        return v

    # Set when the node is answering a phone submitted scan.
    job_id: str | None = Field(default=None, max_length=64)


class IngestAcceptedOut(BaseModel):
    status: Literal["stored", "duplicate"]
    capture_id: str
    gpss_score: int
    risk_level: str
    stress_type: str
    decision: str
    actuator: str
    notify_farmer: bool


class IngestHealthOut(BaseModel):
    status: str
    device: DeviceOut
    site: SiteOut
    server_time: datetime


# --- phone submitted scans -------------------------------------------------


class ScanSubmitOut(BaseModel):
    job_id: str
    kind: Literal["photo", "camera"] = "photo"
    status: str
    queued_at: datetime
    node_online: bool
    message: str | None = None


class ScanStatusOut(BaseModel):
    job_id: str
    kind: Literal["photo", "camera"] = "photo"
    status: str
    capture: CaptureOut | None = None
    error: str | None = None


class ScanJobOut(BaseModel):
    """Handed to a node when it polls for work.

    kind "photo": fetch image_url and score it. kind "camera": there is no image
    yet; take one with the greenhouse camera and score that.
    """

    job_id: str
    kind: Literal["photo", "camera"] = "photo"
    site_id: str
    image_url: str | None = None
    created_at: datetime


class ScanJobFailIn(BaseModel):
    job_id: str
    error: str = Field(max_length=500)

"""Database schema.

Written to work on PostgreSQL (production, Contabo) and SQLite (local work and
tests) without changes, so the same code path is exercised in both.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # Null for accounts that only ever signed in with Google.
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    display_name: Mapped[str | None] = mapped_column(String(120), default=None)
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    sites: Mapped[list["Site"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Opaque rotating refresh tokens. Only the hash is stored."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_agent: Mapped[str | None] = mapped_column(String(255), default=None)


class Site(Base):
    """One greenhouse. A grower may run several."""

    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    # Matches LEAFNODE_SITE_ID on the Pi, so node records stay traceable.
    slug: Mapped[str] = mapped_column(String(64))
    crop: Mapped[str | None] = mapped_column(String(80), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="sites")
    devices: Mapped[list["Device"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_site_user_slug"),)


class Device(Base):
    """A Raspberry Pi node. Authenticates with a bearer token held in its .env."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(
        ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(32), default="pi")
    # sha256 of the token. The plaintext is shown once, at pairing, never stored.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_prefix: Mapped[str] = mapped_column(String(16))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_ip: Mapped[str | None] = mapped_column(String(64), default=None)
    model_version: Mapped[str | None] = mapped_column(String(120), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    site: Mapped[Site] = relationship(back_populates="devices")


class Reading(Base):
    """One environmental sample.

    Every column is nullable because a greenhouse may not have every probe
    wired. The scoring renormalises over whatever actually arrived instead of
    inventing a value for the rest.
    """

    __tablename__ = "readings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(
        ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), default=None
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    soil_moisture: Mapped[float | None] = mapped_column(Float, default=None)
    temperature: Mapped[float | None] = mapped_column(Float, default=None)
    humidity: Mapped[float | None] = mapped_column(Float, default=None)
    light: Mapped[float | None] = mapped_column(Float, default=None)
    soil_raw: Mapped[int | None] = mapped_column(Integer, default=None)
    raw: Mapped[dict | None] = mapped_column(JSON, default=None)

    __table_args__ = (Index("ix_readings_site_time", "site_id", "recorded_at"),)


class Capture(Base):
    """A leaf frame plus the model verdict and the fused decision."""

    __tablename__ = "captures"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(
        ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), default=None
    )
    reading_id: Mapped[str | None] = mapped_column(
        ForeignKey("readings.id", ondelete="SET NULL"), default=None
    )
    # The node's own id for this frame. Unique per device, so the Pi's retry
    # queue can redeliver a row without creating a duplicate here.
    node_capture_id: Mapped[str] = mapped_column(String(80), index=True)
    node_device_id: Mapped[str | None] = mapped_column(String(80), default=None)

    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(16), default="node")  # node | phone

    # --- model output (produced on the Pi, stored verbatim) ---------------
    # Null when the node could not read the photo (dark, no leaf in view). The
    # sensor readings that came with it are still stored and scored.
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    label: Mapped[str | None] = mapped_column(String(120), default=None)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    model_version: Mapped[str | None] = mapped_column(String(120), default=None)
    inference_ms: Mapped[float | None] = mapped_column(Float, default=None)
    extra: Mapped[dict | None] = mapped_column(JSON, default=None)

    # --- fused verdict (computed here from model output + sensors) --------
    gpss_score: Mapped[int] = mapped_column(Integer)
    gpss_risk_level: Mapped[str] = mapped_column(String(16))
    stress_type: Mapped[str] = mapped_column(String(32))
    sub_scores: Mapped[dict] = mapped_column(JSON)
    signals: Mapped[dict] = mapped_column(JSON)  # which inputs were available
    decision: Mapped[str] = mapped_column(String(32))
    actuator: Mapped[str] = mapped_column(String(32))
    notify_farmer: Mapped[bool] = mapped_column(Boolean, default=False)
    decision_reason: Mapped[str] = mapped_column(Text, default="")

    # --- image ------------------------------------------------------------
    image_path: Mapped[str | None] = mapped_column(String(255), default=None)
    image_bytes: Mapped[int | None] = mapped_column(Integer, default=None)
    image_width: Mapped[int | None] = mapped_column(Integer, default=None)
    image_height: Mapped[int | None] = mapped_column(Integer, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("device_id", "node_capture_id", name="uq_capture_device_node"),
        Index("ix_captures_site_time", "site_id", "captured_at"),
    )


class ActuatorEvent(Base):
    """Every autonomous action, so the sustainability figures count real events
    instead of an assumed baseline."""

    __tablename__ = "actuator_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(
        ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    # SET NULL, not CASCADE: the grower clearing their reading history must not
    # erase the record of what the system actually did. The event keeps its own
    # decision, actuator and score, so it stands on its own without the capture.
    capture_id: Mapped[str | None] = mapped_column(
        ForeignKey("captures.id", ondelete="SET NULL"), default=None
    )
    decision: Mapped[str] = mapped_column(String(32))
    actuator: Mapped[str] = mapped_column(String(32))
    gpss_score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_events_site_time", "site_id", "created_at"),)


class ScanJob(Base):
    """Work for the greenhouse node, asked for from the app.

    Two kinds:
      photo   the farmer photographed a leaf with the phone; the node scores it
      camera  the farmer asked the greenhouse camera to take a photo right now

    The phone cannot run the model, and the Pi usually sits behind a router with
    no inbound access. So the Pi polls this queue and dials out with the result.
    Nothing has to be port forwarded.
    """

    __tablename__ = "scan_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(
        ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16), default="photo")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # Empty for a camera job: the photo does not exist until the node takes it.
    image_path: Mapped[str] = mapped_column(String(255))
    claimed_by: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), default=None
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    capture_id: Mapped[str | None] = mapped_column(
        ForeignKey("captures.id", ondelete="SET NULL"), default=None
    )
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

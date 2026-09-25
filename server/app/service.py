"""The work that happens when a reading arrives, in one place.

Both paths end up here: a node reporting on its own schedule, and a node
answering a leaf photo the farmer took in the app. Fusing, storing, recording
the actuator event and waking up connected phones is identical for both.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import storage
from .config import settings
from .deps import as_utc
from .engine.decision import ACTING_DECISIONS, decide
from .engine.diagnosis import Diagnosis, parse_diagnosis
from .engine.gpss import compute_gpss, damage_from_model
from .events import hub
from .models import ActuatorEvent, Capture, Device, Reading, ScanJob, Site
from .schemas import CaptureOut, DiagnosisOut, IngestCaptureIn, ReadingOut

CLOCK_SKEW = timedelta(minutes=5)


def capture_to_out(capture: Capture, reading: Reading | None) -> CaptureOut:
    return CaptureOut(
        id=capture.id,
        site_id=capture.site_id,
        node_capture_id=capture.node_capture_id,
        captured_at=as_utc(capture.captured_at),
        received_at=as_utc(capture.received_at),
        source=capture.source,
        risk_score=capture.risk_score,
        risk_level=capture.risk_level,
        label=capture.label,
        confidence=capture.confidence,
        model_version=capture.model_version,
        inference_ms=capture.inference_ms,
        diagnosis=diagnosis_to_out(parse_diagnosis(capture.extra)),
        gpss_score=capture.gpss_score,
        gpss_risk_level=capture.gpss_risk_level,
        stress_type=capture.stress_type,
        sub_scores=capture.sub_scores or {},
        signals=capture.signals or {},
        decision=capture.decision,
        actuator=capture.actuator,
        notify_farmer=capture.notify_farmer,
        decision_reason=capture.decision_reason or "",
        reading=reading_to_out(reading),
        image_url=(
            f"/api/v1/captures/{capture.id}/image" if capture.image_path else None
        ),
        image_width=capture.image_width,
        image_height=capture.image_height,
    )


def diagnosis_to_out(diagnosis: Diagnosis | None) -> DiagnosisOut | None:
    if diagnosis is None:
        return None
    return DiagnosisOut(
        status=diagnosis.status,
        crop=diagnosis.crop,
        code=diagnosis.code,
        confidence=diagnosis.confidence,
        healthy=diagnosis.healthy,
        uncertain=diagnosis.uncertain,
        disease_found=diagnosis.disease_found,
        reason=diagnosis.reason,
        alternatives=diagnosis.alternatives,
        model=diagnosis.model,
    )


def reading_to_out(reading: Reading | None) -> ReadingOut | None:
    if reading is None:
        return None
    return ReadingOut(
        recorded_at=as_utc(reading.recorded_at),
        soil_moisture=reading.soil_moisture,
        temperature=reading.temperature,
        humidity=reading.humidity,
        light=reading.light,
        soil_raw=reading.soil_raw,
    )


async def find_existing_capture(
    session: AsyncSession, device_id: str, node_capture_id: str
) -> Capture | None:
    """The Pi keeps a disk queue and redelivers after an outage, so the same
    frame can legitimately arrive twice. It must not be stored twice."""
    return (
        await session.execute(
            select(Capture).where(
                Capture.device_id == device_id,
                Capture.node_capture_id == node_capture_id,
            )
        )
    ).scalar_one_or_none()


async def store_capture(
    session: AsyncSession,
    *,
    site: Site,
    device: Device | None,
    payload: IngestCaptureIn,
    source: str = "node",
    image_path: str | None = None,
    image_size: int | None = None,
) -> tuple[Capture, Reading | None]:
    """Fuse the model verdict with the sensors, store everything, notify phones.

    Raises NothingToScore, before anything is written, when the record has
    neither a leaf verdict nor a sensor value.
    """

    now = datetime.now(timezone.utc)
    captured_at = as_utc(payload.received_at) or now
    # The Pi's clock is only as good as its last NTP sync. A reading stamped in
    # the future would sit on top of the dashboard and hide every real one
    # after it, so it is filed under the time it actually arrived.
    if captured_at > now + CLOCK_SKEW:
        captured_at = now

    # --- fuse -------------------------------------------------------------
    # Scored before anything is added to the session, so a record with nothing
    # in it is refused without leaving half of itself behind.
    sensors = payload.sensors
    damage = damage_from_model(payload.risk_score, payload.risk_level)
    diagnosis = parse_diagnosis(payload.extra)
    gpss = compute_gpss(
        damage_percentage=damage,
        soil_moisture=sensors.soil_moisture if sensors else None,
        temperature=sensors.temperature if sensors else None,
        humidity=sensors.humidity if sensors else None,
        light=sensors.light if sensors else None,
    )
    decision = decide(gpss.gpss_score, gpss.stress_type, diagnosis)

    # --- the environmental sample ----------------------------------------
    reading: Reading | None = None
    if sensors is not None:
        known = {"soil_moisture", "temperature", "humidity", "light", "soil_raw"}
        leftovers = {
            k: v for k, v in (sensors.model_extra or {}).items() if k not in known
        }
        reading = Reading(
            site_id=site.id,
            device_id=device.id if device else None,
            recorded_at=captured_at,
            soil_moisture=sensors.soil_moisture,
            temperature=sensors.temperature,
            humidity=sensors.humidity,
            light=sensors.light,
            soil_raw=sensors.soil_raw,
            raw=leftovers or None,
        )
        session.add(reading)
        await session.flush()

    capture = Capture(
        site_id=site.id,
        device_id=device.id if device else None,
        reading_id=reading.id if reading else None,
        node_capture_id=payload.capture_id,
        node_device_id=payload.device_id,
        captured_at=captured_at,
        received_at=now,
        source=source,
        risk_score=damage,
        # No verdict, no leaf risk band: the gpss band describes the sensors.
        risk_level=(
            (payload.risk_level or gpss.risk_level).capitalize() if damage is not None else None
        ),
        label=payload.label,
        confidence=payload.confidence,
        model_version=payload.model_version,
        inference_ms=payload.latency_ms,
        extra=payload.extra,
        gpss_score=gpss.gpss_score,
        gpss_risk_level=gpss.risk_level,
        stress_type=gpss.stress_type,
        sub_scores=gpss.sub_scores,
        signals=gpss.signals,
        decision=decision.decision,
        actuator=decision.actuator,
        notify_farmer=decision.notify_farmer,
        decision_reason=decision.reason,
        image_path=image_path,
        image_bytes=image_size if image_size is not None else payload.image_bytes,
        image_width=payload.image_width,
        image_height=payload.image_height,
    )
    session.add(capture)

    # --- record the action, if it acted -----------------------------------
    if decision.decision in ACTING_DECISIONS or decision.decision == "ALERT_AGRONOMIST":
        await session.flush()
        session.add(
            ActuatorEvent(
                site_id=site.id,
                capture_id=capture.id,
                decision=decision.decision,
                actuator=decision.actuator,
                gpss_score=gpss.gpss_score,
                created_at=now,
            )
        )

    if device is not None and payload.model_version:
        device.model_version = payload.model_version

    await session.commit()
    await session.refresh(capture)
    if reading is not None:
        await session.refresh(reading)

    # --- push to any phone watching this greenhouse -----------------------
    await hub.publish(
        site.id,
        {
            "type": "capture",
            "capture": capture_to_out(capture, reading).model_dump(mode="json"),
        },
    )

    return capture, reading


async def expire_stale_jobs(session: AsyncSession, site_id: str) -> None:
    """A node that claims a job then dies, or never comes for it, must not
    strand the farmer's scan."""
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.scan_job_timeout_seconds
    )
    stale = (
        await session.execute(
            select(ScanJob).where(
                ScanJob.site_id == site_id, ScanJob.status.in_(("pending", "claimed"))
            )
        )
    ).scalars().all()

    changed = False
    for job in stale:
        reference = as_utc(job.claimed_at) or as_utc(job.created_at)
        if reference and reference < cutoff:
            job.status = "expired"
            job.error = "No node answered in time"
            # Nobody is coming for this photo; do not leave it on the disk.
            storage.delete(job.image_path)
            job.image_path = ""
            changed = True
    if changed:
        await session.commit()

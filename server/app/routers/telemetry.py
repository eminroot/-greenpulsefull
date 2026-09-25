"""What the farmer's phone reads: live state, history, trends, savings."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..config import settings
from ..db import get_session
from ..deps import as_utc, current_user, is_online, owned_site
from ..engine.decision import decide
from ..engine.gpss import compute_gpss
from ..models import ActuatorEvent, Capture, Device, Reading, ScanJob, Site, User
from ..ratelimit import scan_limiter
from ..schemas import (
    CaptureOut,
    DeviceStatusOut,
    LiveOut,
    ScanStatusOut,
    ScanSubmitOut,
    ScorePreviewIn,
    ScorePreviewOut,
    SeriesOut,
    SeriesPoint,
    SustainabilityOut,
)
from ..service import capture_to_out, expire_stale_jobs, reading_to_out
from ..uploads import read_upload
from .sites import _site_out

router = APIRouter(tags=["telemetry"])

METRICS = {"soil_moisture", "temperature", "humidity", "light", "gpss_score", "risk_score"}


async def _latest_capture(session: AsyncSession, site_id: str) -> Capture | None:
    return (
        await session.execute(
            select(Capture)
            .where(Capture.site_id == site_id)
            .order_by(Capture.captured_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _latest_reading(session: AsyncSession, site_id: str) -> Reading | None:
    return (
        await session.execute(
            select(Reading)
            .where(Reading.site_id == site_id)
            .order_by(Reading.recorded_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@router.get("/sites/{site_id}/live", response_model=LiveOut)
async def live(
    site: Site = Depends(owned_site),
    session: AsyncSession = Depends(get_session),
) -> LiveOut:
    """The dashboard's state.

    Before a node has ever reported, capture and reading are null. The app shows
    a waiting state for that; it does not fabricate a number.
    """
    capture = await _latest_capture(session, site.id)
    reading = None
    if capture is not None and capture.reading_id:
        reading = await session.get(Reading, capture.reading_id)
    if reading is None:
        reading = await _latest_reading(session, site.id)

    # Through the night every frame is too dark to read, so the newest capture
    # carries sensors only. The last leaf the node could actually see stays on
    # the dashboard rather than vanishing at sunset.
    last_leaf = None
    if capture is not None and capture.risk_score is None:
        last_leaf = (
            await session.execute(
                select(Capture)
                .where(Capture.site_id == site.id, Capture.risk_score.is_not(None))
                .order_by(Capture.captured_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    devices = (
        await session.execute(
            select(Device)
            .where(Device.site_id == site.id, Device.revoked_at.is_(None))
            .order_by(Device.created_at)
        )
    ).scalars().all()

    now = datetime.now(timezone.utc)
    reference = as_utc(reading.recorded_at) if reading else (
        as_utc(capture.captured_at) if capture else None
    )
    seconds_since = (now - reference).total_seconds() if reference else None

    return LiveOut(
        site=await _site_out(session, site),
        capture=capture_to_out(capture, reading) if capture else None,
        last_leaf_capture=capture_to_out(last_leaf, None) if last_leaf else None,
        reading=reading_to_out(reading),
        devices=[
            DeviceStatusOut(
                id=d.id,
                name=d.name,
                online=is_online(as_utc(d.last_seen_at)),
                last_seen_at=as_utc(d.last_seen_at),
                model_version=d.model_version,
            )
            for d in devices
        ],
        online=any(is_online(as_utc(d.last_seen_at)) for d in devices),
        stale=(
            seconds_since is not None
            and seconds_since > settings.device_online_seconds
        ),
        seconds_since_reading=seconds_since,
        server_time=now,
    )


@router.get("/sites/{site_id}/captures", response_model=list[CaptureOut])
async def list_captures(
    site: Site = Depends(owned_site),
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[CaptureOut]:
    stmt = select(Capture).where(Capture.site_id == site.id)
    if before is not None:
        stmt = stmt.where(Capture.captured_at < before)
    stmt = stmt.order_by(Capture.captured_at.desc()).limit(limit)

    captures = (await session.execute(stmt)).scalars().all()

    reading_ids = [c.reading_id for c in captures if c.reading_id]
    readings: dict[str, Reading] = {}
    if reading_ids:
        rows = (
            await session.execute(select(Reading).where(Reading.id.in_(reading_ids)))
        ).scalars().all()
        readings = {r.id: r for r in rows}

    return [
        capture_to_out(c, readings.get(c.reading_id) if c.reading_id else None)
        for c in captures
    ]


@router.delete("/sites/{site_id}/captures", status_code=204)
async def clear_captures(
    site: Site = Depends(owned_site),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Clears this greenhouse's stored readings and their leaf photos.

    Actuator events are kept: they are the record of what the system actually
    did, and the savings figures are counted from them.
    """
    captures = (
        await session.execute(select(Capture).where(Capture.site_id == site.id))
    ).scalars().all()

    for capture in captures:
        storage.delete(capture.image_path)
        await session.delete(capture)
    await session.commit()


@router.get("/sites/{site_id}/series", response_model=SeriesOut)
async def series(
    metric: str = Query(...),
    hours: int = Query(default=24, ge=1, le=24 * 30),
    site: Site = Depends(owned_site),
    session: AsyncSession = Depends(get_session),
) -> SeriesOut:
    """Points for the trend charts, oldest first."""
    if metric not in METRICS:
        raise HTTPException(status_code=400, detail="unknown_metric")

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    if metric in {"gpss_score", "risk_score"}:
        column = getattr(Capture, metric)
        rows = (
            await session.execute(
                select(Capture.captured_at, column)
                # A photo the node could not read has no leaf risk; it is a
                # gap in that line, not a zero.
                .where(
                    Capture.site_id == site.id,
                    Capture.captured_at >= since,
                    column.is_not(None),
                )
                .order_by(Capture.captured_at)
            )
        ).all()
    else:
        column = getattr(Reading, metric)
        rows = (
            await session.execute(
                select(Reading.recorded_at, column)
                .where(
                    Reading.site_id == site.id,
                    Reading.recorded_at >= since,
                    column.is_not(None),
                )
                .order_by(Reading.recorded_at)
            )
        ).all()

    return SeriesOut(
        metric=metric,
        points=[SeriesPoint(t=as_utc(t), v=v) for t, v in rows],
    )


@router.get("/sites/{site_id}/sustainability", response_model=SustainabilityOut)
async def sustainability(
    site: Site = Depends(owned_site),
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> SustainabilityOut:
    """Savings figures derived from actions this greenhouse actually took.

    The counters are real: every row in actuator_events was a decision the
    system made on a real reading. The money, water and CO2 figures on top of
    them are estimates from published per event rates, not measurements.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    counts = dict(
        (
            await session.execute(
                select(ActuatorEvent.decision, func.count())
                .where(ActuatorEvent.site_id == site.id, ActuatorEvent.created_at >= since)
                .group_by(ActuatorEvent.decision)
            )
        ).all()
    )
    capture_count = (
        await session.execute(
            select(func.count())
            .select_from(Capture)
            .where(Capture.site_id == site.id, Capture.captured_at >= since)
        )
    ).scalar_one()

    irrigation = counts.get("IRRIGATION_ON", 0)
    ventilation = counts.get("VENTILATION_ON", 0)
    light_events = counts.get("SUPPLEMENTAL_LIGHT_ON", 0)
    alerts = counts.get("ALERT_AGRONOMIST", 0)
    autonomous = irrigation + ventilation + light_events

    # Same curves the app used before, now fed by real counts starting at zero
    # instead of an assumed baseline.
    water_saved = round(45 * (1 - math.exp(-irrigation / 7))) if irrigation else 0
    energy_saved = round(30 * (1 - math.exp(-autonomous / 9))) if autonomous else 0

    cost_reduction = round(1200 * water_saved / 100 + 1500 * energy_saved / 100)
    co2 = round((600 * energy_saved / 100) * 0.45 + water_saved * 0.6)
    water_liters = round(12000 * water_saved / 100)
    clamp = lambda v, hi: int(max(0, min(hi, round(v))))  # noqa: E731

    first_event = (
        await session.execute(
            select(func.min(ActuatorEvent.created_at)).where(
                ActuatorEvent.site_id == site.id
            )
        )
    ).scalar_one_or_none()

    return SustainabilityOut(
        irrigation_events=irrigation,
        ventilation_events=ventilation,
        light_events=light_events,
        autonomous_actions=autonomous,
        alerts=alerts,
        captures=capture_count,
        water_saved_pct=water_saved,
        energy_saved_pct=energy_saved,
        cost_reduction=cost_reduction,
        co2_kg=co2,
        water_liters=water_liters,
        yield_protected_pct=clamp(water_saved * 0.3 + energy_saved * 0.18, 24),
        disease_risk_pct=clamp(ventilation * 3.5, 45) if ventilation else 0,
        manual_checks=autonomous,
        labor_hours=round(autonomous * 0.6),
        fertilizer_saved_pct=clamp(water_saved * 0.4, 25),
        since=as_utc(first_event),
    )


@router.post("/score/preview", response_model=ScorePreviewOut)
async def score_preview(
    body: ScorePreviewIn,
    user: User = Depends(current_user),
) -> ScorePreviewOut:
    """Scores a hypothetical reading without storing anything.

    Same engine, same weights, same thresholds as a real reading, so what the
    panel's twin shows is exactly what the greenhouse would do. It writes
    nothing and produces no actuator event.
    """
    gpss = compute_gpss(
        damage_percentage=body.damage_percentage,
        soil_moisture=body.soil_moisture,
        temperature=body.temperature,
        humidity=body.humidity,
        light=body.light,
    )
    decision = decide(gpss.gpss_score, gpss.stress_type)

    return ScorePreviewOut(
        gpss_score=gpss.gpss_score,
        risk_level=gpss.risk_level,
        stress_type=gpss.stress_type,
        sub_scores=gpss.sub_scores,
        signals=gpss.signals,
        decision=decision.decision,
        actuator=decision.actuator,
        notify_farmer=decision.notify_farmer,
        decision_reason=decision.reason,
    )


# --- leaf photo taken in the app -------------------------------------------


@router.post("/sites/{site_id}/scans", response_model=ScanSubmitOut, status_code=202)
async def submit_scan(
    response: Response,
    image: UploadFile = File(...),
    site: Site = Depends(owned_site),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ScanSubmitOut:
    """Queues a leaf photo for the greenhouse node to score.

    The phone has no model on it, so this returns immediately with a job id and
    the app watches for the result over the websocket.
    """
    # Metered: each scan stores a photo and puts work on the greenhouse node.
    if not scan_limiter.hit(user.id):
        response.headers["Retry-After"] = str(scan_limiter.retry_after(user.id))
        raise HTTPException(status_code=429, detail="too_many_scans")

    data = await read_upload(image)

    job = ScanJob(site_id=site.id, user_id=user.id, image_path="")
    session.add(job)
    await session.flush()

    try:
        path, _ = storage.save_image(data, site_id=site.id, kind="scans", key=job.id)
    except storage.ImageTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except (storage.UnsupportedImage, storage.UnsafeName) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job.image_path = path
    await session.commit()

    return await _submitted(session, site, job)


@router.post("/sites/{site_id}/camera/capture", response_model=ScanSubmitOut, status_code=202)
async def request_camera_capture(
    response: Response,
    site: Site = Depends(owned_site),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ScanSubmitOut:
    """Asks the greenhouse camera to photograph the leaf now, off schedule.

    Same road as a phone scan: the node picks the job up on its next poll, has
    the ESP32 take the photo, scores it and reports it like any other reading.
    The app follows the job at /scans/{job_id}.
    """
    # A second tap while the camera is still busy is the same request, not a
    # second photo. Handing back the open job also keeps the queue from
    # filling with shots nobody is waiting for.
    await expire_stale_jobs(session, site.id)
    open_job = (
        await session.execute(
            select(ScanJob)
            .where(
                ScanJob.site_id == site.id,
                ScanJob.kind == "camera",
                ScanJob.status.in_(("pending", "claimed")),
            )
            .order_by(ScanJob.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if open_job is not None:
        return await _submitted(session, site, open_job)

    # Metered like a phone scan: each one wakes the camera and runs the model.
    if not scan_limiter.hit(user.id):
        response.headers["Retry-After"] = str(scan_limiter.retry_after(user.id))
        raise HTTPException(status_code=429, detail="too_many_scans")

    job = ScanJob(site_id=site.id, user_id=user.id, kind="camera", image_path="")
    session.add(job)
    await session.commit()
    return await _submitted(session, site, job)


async def _submitted(session: AsyncSession, site: Site, job: ScanJob) -> ScanSubmitOut:
    devices = (
        await session.execute(
            select(Device).where(Device.site_id == site.id, Device.revoked_at.is_(None))
        )
    ).scalars().all()
    node_online = any(is_online(as_utc(d.last_seen_at)) for d in devices)

    return ScanSubmitOut(
        job_id=job.id,
        kind=job.kind,
        status=job.status,
        queued_at=as_utc(job.created_at),
        node_online=node_online,
        message=None if node_online else "no_node_online",
    )


@router.get("/scans/{job_id}", response_model=ScanStatusOut)
async def scan_status(
    job_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ScanStatusOut:
    job = await session.get(ScanJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="job_not_found")
    # Jobs are otherwise only expired when a node polls, and a node that is off
    # never polls. Without this the farmer would watch "pending" forever.
    await expire_stale_jobs(session, job.site_id)

    capture_out = None
    if job.capture_id:
        capture = await session.get(Capture, job.capture_id)
        if capture is not None:
            reading = (
                await session.get(Reading, capture.reading_id)
                if capture.reading_id
                else None
            )
            capture_out = capture_to_out(capture, reading)

    return ScanStatusOut(
        job_id=job.id, kind=job.kind, status=job.status, capture=capture_out, error=job.error
    )

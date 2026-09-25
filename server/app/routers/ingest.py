"""Everything the Raspberry Pi talks to.

The node authenticates with the bearer token it holds in its .env and never
sees a user account. Two directions:

  up    POST /ingest/capture          a reading the node produced on its own
  down  GET  /ingest/jobs             work the farmer asked for in the app: a
                                      leaf photo they took, or a request for
                                      the greenhouse camera to take one now

The download direction exists because the Pi normally sits behind a router with
no inbound access. It dials out for work, so nothing has to be port forwarded.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..db import get_session
from ..deps import as_utc, current_device
from ..engine.diagnosis import parse_diagnosis
from ..engine.gpss import NothingToScore
from ..events import job_wakeups
from ..models import Capture, Device, ScanJob, Site
from ..schemas import (
    DeviceOut,
    IngestAcceptedOut,
    IngestCaptureIn,
    IngestHealthOut,
    ScanJobFailIn,
    ScanJobOut,
    SiteOut,
)
from ..service import expire_stale_jobs, find_existing_capture, store_capture
from ..uploads import read_upload

router = APIRouter(prefix="/ingest", tags=["ingest"])

# How long a node may hold /jobs open waiting for work. Long enough that a scan
# feels immediate to the farmer, short enough to sit well inside proxy timeouts.
JOB_WAIT_SECONDS = 25
# Only the safety net: a new job wakes the poll straight away (events.py).
JOB_POLL_INTERVAL = 5.0
JOB_KINDS = {"photo", "camera"}


async def _site_for(session: AsyncSession, device: Device) -> Site:
    site = await session.get(Site, device.site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="site_missing")
    return site


@router.get("/health", response_model=IngestHealthOut)
async def ingest_health(
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> IngestHealthOut:
    """Lets the node confirm its token and URL are right before it has data."""
    site = await _site_for(session, device)
    return IngestHealthOut(
        status="ok",
        device=DeviceOut(
            id=device.id,
            site_id=device.site_id,
            name=device.name,
            kind=device.kind,
            token_prefix=device.token_prefix,
            online=True,
            last_seen_at=as_utc(device.last_seen_at),
            model_version=device.model_version,
            created_at=as_utc(device.created_at),
        ),
        site=SiteOut(
            id=site.id,
            name=site.name,
            slug=site.slug,
            crop=site.crop,
            created_at=as_utc(site.created_at),
        ),
        server_time=datetime.now(timezone.utc),
    )


@router.post("/capture", response_model=IngestAcceptedOut)
async def ingest_capture(
    payload: IngestCaptureIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> IngestAcceptedOut:
    """Accepts the record pi/uploader.py sends.

    site_id and device_id in the body are kept for traceability but are not
    trusted for authorisation: the token decides which greenhouse this writes
    to, so a leaked node token cannot be pointed at somebody else's data.
    """
    site = await _site_for(session, device)

    existing = await find_existing_capture(session, device.id, payload.capture_id)
    if existing is not None:
        # The node redelivered after an outage. Answer 200 so its queue drops
        # the row instead of retrying forever. If the first delivery answered a
        # phone scan but never closed it (it raced a second copy of the same
        # verdict), close it now, or the farmer is told no node answered.
        if payload.job_id:
            await _close_job(session, payload.job_id, site.id, existing)
        return IngestAcceptedOut(
            status="duplicate",
            capture_id=existing.id,
            gpss_score=existing.gpss_score,
            risk_level=existing.gpss_risk_level,
            stress_type=existing.stress_type,
            decision=existing.decision,
            actuator=existing.actuator,
            notify_farmer=existing.notify_farmer,
        )

    if payload.risk_score is None and not payload.risk_level:
        # Allowed only when the node says it looked and could not read the
        # photo. That record still carries the sensors, which keep the
        # greenhouse scored through the night.
        verdict = parse_diagnosis(payload.extra)
        if verdict is None or verdict.status != "unreadable":
            raise HTTPException(status_code=400, detail="risk_score_or_level_required")

    image_path = None
    image_size = None
    if payload.image_b64:
        try:
            data = storage.decode_base64(payload.image_b64)
            image_path, image_size = storage.save_image(
                data, site_id=site.id, kind="captures", key=payload.capture_id
            )
        except storage.ImageTooLarge as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except (storage.UnsupportedImage, storage.UnsafeName) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    source = "node"
    if payload.job_id:
        job = await session.get(ScanJob, payload.job_id)
        # A photo the camera took on request is still the node's own frame.
        # Only a photo the farmer took with the phone is marked as the phone's.
        if job is None or job.site_id != site.id or job.kind != "camera":
            source = "phone"
    try:
        capture, _ = await store_capture(
            session,
            site=site,
            device=device,
            payload=payload,
            source=source,
            image_path=image_path,
            image_size=image_size,
        )
    except NothingToScore as exc:
        # An unreadable photo with no sensor values. 422, so the node files it
        # as undeliverable instead of retrying it forever.
        storage.delete(image_path)
        raise HTTPException(status_code=422, detail="nothing_to_score") from exc

    # If this answers a phone submitted scan, close that job out.
    if payload.job_id:
        await _close_job(session, payload.job_id, site.id, capture)

    return IngestAcceptedOut(
        status="stored",
        capture_id=capture.id,
        gpss_score=capture.gpss_score,
        risk_level=capture.gpss_risk_level,
        stress_type=capture.stress_type,
        decision=capture.decision,
        actuator=capture.actuator,
        notify_farmer=capture.notify_farmer,
    )


async def _close_job(
    session: AsyncSession, job_id: str, site_id: str, capture: Capture
) -> None:
    job = await session.get(ScanJob, job_id)
    if job is None or job.site_id != site_id or job.status == "done":
        return
    job.status = "done"
    job.error = None
    job.capture_id = capture.id
    capture.source = "node" if job.kind == "camera" else "phone"
    if not capture.image_path:
        # The scan photo is already on disk; hand it to the capture rather than
        # keeping two copies of the same leaf. Empty if the job had expired and
        # the photo was already cleaned up.
        capture.image_path = job.image_path or None
    else:
        # The node sent its own frame, so the queued one is now orphaned.
        # Remove it instead of leaving it to fill the disk.
        storage.delete(job.image_path)
    job.image_path = ""
    await session.commit()


@router.post("/capture/{node_capture_id}/image", status_code=204)
async def ingest_capture_image(
    node_capture_id: str,
    image: UploadFile = File(...),
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Attaches the JPEG to a capture already sent as JSON.

    Two requests rather than one so a slow or failed image upload never costs
    the reading itself.
    """
    capture = await find_existing_capture(session, device.id, node_capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="capture_not_found")

    data = await read_upload(image)
    try:
        path, size = storage.save_image(
            data, site_id=capture.site_id, kind="captures", key=capture.id
        )
    except storage.ImageTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except (storage.UnsupportedImage, storage.UnsafeName) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    capture.image_path = path
    capture.image_bytes = size
    await session.commit()


# --- work queue: what the farmer asked for in the app ----------------------


@router.get("/jobs", response_model=ScanJobOut | None)
async def claim_job(
    response: Response,
    wait: int = JOB_WAIT_SECONDS,
    kinds: str = "photo",
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
):
    """Long polls for work: a leaf photo to score, or a photo to take.

    `kinds` lists what this node can do, comma separated. It defaults to
    "photo" so an agent from before camera requests existed is never handed
    a job it would not understand; that job waits for a node that can.

    Returns 204 when nothing turns up within the wait, and the node simply
    polls again.
    """
    site_id = device.site_id
    wanted = {k.strip() for k in kinds.split(",")} & JOB_KINDS or {"photo"}
    deadline = asyncio.get_running_loop().time() + max(0, min(wait, JOB_WAIT_SECONDS))

    while True:
        ready = job_wakeups.waiter(site_id)
        await expire_stale_jobs(session, site_id)
        job = (
            await session.execute(
                select(ScanJob)
                .where(
                    ScanJob.site_id == site_id,
                    ScanJob.status == "pending",
                    ScanJob.kind.in_(wanted),
                )
                .order_by(ScanJob.created_at)
                .limit(1)
            )
        ).scalar_one_or_none()

        if job is not None:
            job.status = "claimed"
            job.claimed_by = device.id
            job.claimed_at = datetime.now(timezone.utc)
            await session.commit()
            return ScanJobOut(
                job_id=job.id,
                kind=job.kind,
                site_id=job.site_id,
                image_url=(
                    f"/api/v1/ingest/jobs/{job.id}/image" if job.kind == "photo" else None
                ),
                created_at=as_utc(job.created_at),
            )

        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            response.status_code = status.HTTP_204_NO_CONTENT
            return None

        try:
            await asyncio.wait_for(ready.wait(), timeout=min(remaining, JOB_POLL_INTERVAL))
        except asyncio.TimeoutError:
            pass


@router.get("/jobs/{job_id}/image")
async def job_image(
    job_id: str,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    job = await session.get(ScanJob, job_id)
    if job is None or job.site_id != device.site_id:
        raise HTTPException(status_code=404, detail="job_not_found")

    path = storage.resolve(job.image_path)
    if path is None:
        raise HTTPException(status_code=404, detail="image_missing")
    return FileResponse(path, media_type=storage.content_type_for(path))


@router.post("/jobs/fail", status_code=204)
async def fail_job(
    body: ScanJobFailIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    """The node could not do the job (model missing, bad frame, camera did
    not answer). `error` is shown to the farmer as a reason, so the node sends
    a code such as "unreadable:too_dark" or "camera_unreachable"."""
    job = await session.get(ScanJob, body.job_id)
    if job is None or job.site_id != device.site_id:
        raise HTTPException(status_code=404, detail="job_not_found")
    job.status = "failed"
    job.error = body.error
    # Nothing will ever read this photo now.
    storage.delete(job.image_path)
    job.image_path = ""
    await session.commit()

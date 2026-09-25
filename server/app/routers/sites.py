"""Greenhouses and the nodes paired to them."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import as_utc, current_user, is_online, owned_site
from ..models import Capture, Device, Site, User
from ..schemas import (
    DeviceCreatedOut,
    DeviceCreateIn,
    DeviceOut,
    SiteCreateIn,
    SiteOut,
)
from ..security import create_device_token

router = APIRouter(tags=["sites"])


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:64] or "site"


async def _site_out(session: AsyncSession, site: Site) -> SiteOut:
    devices = (
        await session.execute(select(Device).where(Device.site_id == site.id))
    ).scalars().all()
    last_capture_at = (
        await session.execute(
            select(func.max(Capture.captured_at)).where(Capture.site_id == site.id)
        )
    ).scalar_one_or_none()

    return SiteOut(
        id=site.id,
        name=site.name,
        slug=site.slug,
        crop=site.crop,
        created_at=as_utc(site.created_at),
        device_count=len(devices),
        online=any(is_online(as_utc(d.last_seen_at)) for d in devices if d.revoked_at is None),
        last_capture_at=as_utc(last_capture_at),
    )


def _device_out(device: Device) -> DeviceOut:
    return DeviceOut(
        id=device.id,
        site_id=device.site_id,
        name=device.name,
        kind=device.kind,
        token_prefix=device.token_prefix,
        online=is_online(as_utc(device.last_seen_at)),
        last_seen_at=as_utc(device.last_seen_at),
        model_version=device.model_version,
        created_at=as_utc(device.created_at),
    )


@router.get("/sites", response_model=list[SiteOut])
async def list_sites(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SiteOut]:
    sites = (
        await session.execute(
            select(Site).where(Site.user_id == user.id).order_by(Site.created_at)
        )
    ).scalars().all()
    return [await _site_out(session, s) for s in sites]


@router.post("/sites", response_model=SiteOut, status_code=201)
async def create_site(
    body: SiteCreateIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> SiteOut:
    slug = _slugify(body.slug or body.name)

    taken = (
        await session.execute(
            select(Site.id).where(Site.user_id == user.id, Site.slug == slug)
        )
    ).scalar_one_or_none()
    if taken:
        raise HTTPException(status_code=409, detail="slug_in_use")

    site = Site(user_id=user.id, name=body.name.strip(), slug=slug, crop=body.crop)
    session.add(site)
    await session.commit()
    await session.refresh(site)
    return await _site_out(session, site)


@router.get("/sites/{site_id}", response_model=SiteOut)
async def get_site(
    site: Site = Depends(owned_site),
    session: AsyncSession = Depends(get_session),
) -> SiteOut:
    return await _site_out(session, site)


@router.delete("/sites/{site_id}", status_code=204)
async def delete_site(
    site: Site = Depends(owned_site),
    session: AsyncSession = Depends(get_session),
) -> None:
    from ..config import settings

    site_dir = settings.data_dir / site.id
    if site_dir.is_dir():
        for path in sorted(site_dir.rglob("*"), reverse=True):
            path.unlink(missing_ok=True) if path.is_file() else path.rmdir()
        site_dir.rmdir()

    await session.delete(site)
    await session.commit()


# --- devices ---------------------------------------------------------------


@router.get("/sites/{site_id}/devices", response_model=list[DeviceOut])
async def list_devices(
    site: Site = Depends(owned_site),
    session: AsyncSession = Depends(get_session),
) -> list[DeviceOut]:
    devices = (
        await session.execute(
            select(Device)
            .where(Device.site_id == site.id, Device.revoked_at.is_(None))
            .order_by(Device.created_at)
        )
    ).scalars().all()
    return [_device_out(d) for d in devices]


@router.post("/sites/{site_id}/devices", response_model=DeviceCreatedOut, status_code=201)
async def pair_device(
    body: DeviceCreateIn,
    site: Site = Depends(owned_site),
    session: AsyncSession = Depends(get_session),
) -> DeviceCreatedOut:
    """Pairs a Raspberry Pi and hands back its token.

    This is the only time the token is readable. It goes into the node's .env;
    if it is lost, pair the device again and the old token stops working.
    """
    raw, token_hash, prefix = create_device_token()
    device = Device(
        site_id=site.id,
        name=body.name.strip(),
        kind=body.kind,
        token_hash=token_hash,
        token_prefix=prefix,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)

    return DeviceCreatedOut(
        **_device_out(device).model_dump(),
        token=raw,
        setup={
            "LEAFNODE_UPSTREAM_URL": "https://<your-server>/api/v1/ingest/capture",
            "LEAFNODE_UPSTREAM_TOKEN": raw,
            "LEAFNODE_SITE_ID": site.slug,
        },
    )


@router.delete("/devices/{device_id}", status_code=204)
async def revoke_device(
    device_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device_not_found")

    site = await session.get(Site, device.site_id)
    if site is None or site.user_id != user.id:
        raise HTTPException(status_code=404, detail="device_not_found")

    # Revoked rather than deleted, so the captures it produced keep their
    # provenance.
    device.revoked_at = datetime.now(timezone.utc)
    await session.commit()

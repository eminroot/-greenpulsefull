"""Shared FastAPI dependencies: who is calling, and what may they touch."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session
from .models import Device, Site, User
from .security import decode_access_token, sha256

bearer = HTTPBearer(auto_error=False)


def _unauthorised(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if creds is None or not creds.credentials:
        raise _unauthorised("Missing bearer token")

    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise _unauthorised("Invalid or expired access token")

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorised("Account is not available")
    return user


async def current_device(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> Device:
    """Authenticates a Raspberry Pi by the token in its .env.

    Also records that the node was heard from, which is what the app uses to
    decide whether a greenhouse is online.
    """
    if creds is None or not creds.credentials:
        raise _unauthorised("Missing device token")

    token_hash = sha256(creds.credentials.strip())
    device = (
        await session.execute(select(Device).where(Device.token_hash == token_hash))
    ).scalar_one_or_none()

    if device is None or device.revoked_at is not None:
        raise _unauthorised("Unknown or revoked device token")

    device.last_seen_at = datetime.now(timezone.utc)
    if request.client:
        device.last_ip = request.client.host
    await session.commit()
    return device


async def owned_site(
    site_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Site:
    site = await session.get(Site, site_id)
    # A site belonging to somebody else is reported as missing rather than
    # forbidden, so this cannot be used to probe for valid ids.
    if site is None or site.user_id != user.id:
        raise HTTPException(status_code=404, detail="Greenhouse not found")
    return site


def is_online(last_seen_at: datetime | None) -> bool:
    if last_seen_at is None:
        return False
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.device_online_seconds)
    return last_seen_at >= cutoff


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; normalise so comparisons are safe."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

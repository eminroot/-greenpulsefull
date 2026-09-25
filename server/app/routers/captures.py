"""A single stored capture: read it, look at the leaf, remove it."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..db import get_session
from ..deps import current_user
from ..models import Capture, Reading, Site, User
from ..schemas import CaptureOut
from ..service import capture_to_out

router = APIRouter(prefix="/captures", tags=["captures"])


async def _owned_capture(
    capture_id: str, user: User, session: AsyncSession
) -> Capture:
    capture = await session.get(Capture, capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="capture_not_found")
    site = await session.get(Site, capture.site_id)
    if site is None or site.user_id != user.id:
        raise HTTPException(status_code=404, detail="capture_not_found")
    return capture


@router.get("/{capture_id}", response_model=CaptureOut)
async def get_capture(
    capture_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureOut:
    capture = await _owned_capture(capture_id, user, session)
    reading = (
        await session.get(Reading, capture.reading_id) if capture.reading_id else None
    )
    return capture_to_out(capture, reading)


@router.get("/{capture_id}/image")
async def capture_image(
    capture_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    capture = await _owned_capture(capture_id, user, session)
    path = storage.resolve(capture.image_path or "")
    if path is None:
        raise HTTPException(status_code=404, detail="image_not_found")
    return FileResponse(
        path,
        media_type=storage.content_type_for(path),
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.delete("/{capture_id}", status_code=204)
async def delete_capture(
    capture_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    capture = await _owned_capture(capture_id, user, session)
    storage.delete(capture.image_path)
    await session.delete(capture)
    await session.commit()

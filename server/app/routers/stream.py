"""Live push to the farmer's phone and to the web panel.

A websocket per open dashboard. When a node uploads a reading, every client
watching that greenhouse has the new numbers before the request that delivered
them has finished.

Opening the socket takes a ticket, not an access token. A browser cannot set an
Authorization header on a WebSocket, so the credential has to go in the URL,
where the reverse proxy logs it; a ticket that lives for a minute and works once
is worthless by the time anyone reads that log, while an access token would be
good for half an hour.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal
from ..deps import owned_site
from ..events import hub
from ..models import Site
from ..tickets import tickets

router = APIRouter(tags=["stream"])

# Keeps mobile carriers and reverse proxies from dropping an idle connection.
HEARTBEAT_SECONDS = 25


class StreamTicketOut(BaseModel):
    ticket: str
    expires_in: int


@router.post("/sites/{site_id}/stream/ticket", response_model=StreamTicketOut)
async def stream_ticket(site: Site = Depends(owned_site)) -> StreamTicketOut:
    """Mints a one minute, single use ticket for this greenhouse's stream."""
    ticket, ttl = tickets.issue(user_id=site.user_id, site_id=site.id)
    return StreamTicketOut(ticket=ticket, expires_in=ttl)


async def _authorise(session: AsyncSession, ticket: str, site_id: str) -> bool:
    user_id = tickets.redeem(ticket, site_id=site_id)
    if user_id is None:
        return False
    # The ticket is bound to a site, but confirm ownership still holds: a site
    # can be deleted, or handed over, between minting and connecting.
    site = await session.get(Site, site_id)
    return site is not None and site.user_id == user_id


@router.websocket("/sites/{site_id}/stream")
async def stream(websocket: WebSocket, site_id: str, ticket: str = Query(default="")):
    async with SessionLocal() as session:
        allowed = await _authorise(session, ticket, site_id)

    if not allowed:
        # Closed before accepting, so a bad ticket never opens a socket.
        await websocket.close(code=4401)
        return

    await websocket.accept()
    queue = await hub.subscribe(site_id)

    await websocket.send_json(
        {"type": "ready", "site_id": site_id, "at": datetime.now(timezone.utc).isoformat()}
    )

    async def pump_incoming() -> None:
        # The clients do not send us anything, but reading is how a closed
        # dashboard is noticed, and it drains any client pings. A disconnect is
        # the normal way this ends, so it returns rather than raising.
        try:
            while True:
                await websocket.receive_text()
        except (WebSocketDisconnect, RuntimeError):
            return

    reader = asyncio.create_task(pump_incoming())
    try:
        while True:
            pending = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait(
                {pending, reader},
                timeout=HEARTBEAT_SECONDS,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if reader in done:
                # The client went away. Stop before writing to a dead socket.
                pending.cancel()
                break

            if pending in done:
                await websocket.send_json(pending.result())
                continue

            pending.cancel()
            await websocket.send_json(
                {"type": "ping", "at": datetime.now(timezone.utc).isoformat()}
            )
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        reader.cancel()
        with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
            await reader
        await hub.unsubscribe(site_id, queue)

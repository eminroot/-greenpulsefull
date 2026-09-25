"""Short lived, single use tickets for opening a websocket.

A browser cannot set an Authorization header on a WebSocket, so the credential
has to travel in the URL. Putting the access token there means it lands in the
reverse proxy's access log, where it stays readable for as long as the log is
kept, and an access token is good for half an hour.

A ticket avoids that: it is issued over an authenticated POST, lives for a
minute, works once, and grants nothing except a stream for the one greenhouse it
was minted for. A ticket in a log file is already useless by the time anyone
reads it.

In process, like the event hub, which is why the container runs a single worker.
Moving both to Redis is the same change.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass

TICKET_TTL_SECONDS = 60
_MAX_OUTSTANDING = 10_000


@dataclass(frozen=True)
class Ticket:
    user_id: str
    site_id: str
    expires_at: float


class TicketStore:
    def __init__(self) -> None:
        self._tickets: dict[str, Ticket] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        """Called under the lock."""
        expired = [key for key, t in self._tickets.items() if t.expires_at <= now]
        for key in expired:
            self._tickets.pop(key, None)
        # Unredeemed tickets are cheap but not free; never grow without bound.
        if len(self._tickets) >= _MAX_OUTSTANDING:
            self._tickets.clear()

    def issue(self, *, user_id: str, site_id: str) -> tuple[str, int]:
        now = time.monotonic()
        ticket = secrets.token_urlsafe(32)
        with self._lock:
            self._prune(now)
            self._tickets[ticket] = Ticket(
                user_id=user_id, site_id=site_id, expires_at=now + TICKET_TTL_SECONDS
            )
        return ticket, TICKET_TTL_SECONDS

    def redeem(self, ticket: str, *, site_id: str) -> str | None:
        """Consume a ticket and return the user it belongs to, or None.

        Single use: even if the URL is logged or shoulder surfed, replaying it
        gets nothing.
        """
        if not ticket:
            return None
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            found = self._tickets.pop(ticket, None)
        if found is None or found.expires_at <= now or found.site_id != site_id:
            return None
        return found.user_id


tickets = TicketStore()

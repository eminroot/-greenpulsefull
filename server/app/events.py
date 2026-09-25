"""Live fan out from ingest to connected phones.

An in process broker: a reading arrives from a node, every websocket currently
watching that greenhouse gets it immediately. Good for a single uvicorn worker,
which is what one greenhouse operation needs. If this ever runs multiple
workers, swap the body of publish/subscribe for Redis pub/sub; nothing outside
this file needs to change.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict
from typing import Any

# Bounded so a phone that stops reading (backgrounded, bad signal) cannot grow
# the queue without limit. The oldest frame is dropped instead.
QUEUE_SIZE = 32


class EventHub:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, site_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        async with self._lock:
            self._subscribers[site_id].add(queue)
        return queue

    async def unsubscribe(self, site_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            subs = self._subscribers.get(site_id)
            if subs:
                subs.discard(queue)
                if not subs:
                    self._subscribers.pop(site_id, None)

    async def publish(self, site_id: str, event: dict[str, Any]) -> int:
        async with self._lock:
            targets = list(self._subscribers.get(site_id, ()))
        delivered = 0
        for queue in targets:
            if queue.full():
                # Drop the oldest so the newest state always gets through.
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(event)
                delivered += 1
        return delivered

    def listener_count(self, site_id: str) -> int:
        return len(self._subscribers.get(site_id, ()))


hub = EventHub()


class Wakeups:
    """Wakes a long poll the moment there is work for it.

    The Pi holds GET /ingest/jobs open waiting for a scan or a camera request.
    Without this it would find a new job only on its next look at the
    database; with it, queueing the job wakes the poll at once. The periodic
    look stays as the safety net.
    """

    def __init__(self) -> None:
        self._events: dict[str, asyncio.Event] = {}

    def waiter(self, key: str) -> asyncio.Event:
        """Take this before checking for work, so a job queued in between still
        wakes the wait that follows."""
        event = self._events.get(key)
        if event is None or event.is_set():
            event = self._events[key] = asyncio.Event()
        return event

    def notify(self, key: str) -> None:
        event = self._events.pop(key, None)
        if event is not None:
            event.set()


job_wakeups = Wakeups()

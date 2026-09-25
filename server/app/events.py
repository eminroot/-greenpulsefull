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

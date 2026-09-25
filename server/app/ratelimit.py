"""A small in-process rate limiter.

Sized for one uvicorn worker, which is what one greenhouse operation runs. It
exists to stop password guessing and to keep a stolen account from running up a
bill on the assistant, not to survive a distributed attack: a reverse proxy or
Redis is the right tool for that, and the shape of this module is the same
either way.

The bookkeeping prunes itself. An earlier version kept a dict entry per
(ip, email) pair forever, which is a slow memory leak an attacker can drive.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from .config import settings

# (keys are swept once their window lapses; see _sweep)
# Hard ceiling on tracked keys, so a flood of unique keys cannot exhaust memory.
_MAX_KEYS = 20_000


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float, name: str = "") -> None:
        self.limit = limit
        self.window = window_seconds
        self.name = name
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    def _sweep(self, now: float) -> None:
        """Drop keys that no longer carry information. Called under the lock.

        Once a key's newest hit falls outside the window it counts for nothing,
        so there is no reason to keep it. Sweeping on that rather than on a
        fixed idle timeout is what keeps the table proportional to live traffic
        instead of to every address that has ever been seen.
        """
        if now - self._last_sweep < 60 and len(self._hits) < _MAX_KEYS:
            return
        self._last_sweep = now

        stale = [
            key
            for key, hits in self._hits.items()
            if not hits or now - hits[-1] > self.window
        ]
        for key in stale:
            self._hits.pop(key, None)

        # Still too many live keys: that is an attack, not traffic. Start clean
        # rather than grow without bound.
        if len(self._hits) >= _MAX_KEYS:
            self._hits.clear()

    def check(self, key: str) -> bool:
        """True when the caller is within the limit. Does not record anything."""
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            hits = self._hits.get(key)
            if not hits:
                return True
            while hits and now - hits[0] > self.window:
                hits.popleft()
            return len(hits) < self.limit

    def record(self, key: str) -> None:
        """Count one attempt against the key."""
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self.window:
                hits.popleft()
            hits.append(now)

    def hit(self, key: str) -> bool:
        """Record an attempt and say whether it was allowed.

        Use this for anything metered by request (the assistant). Use
        check/record separately where only failures should count (sign in).
        """
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def retry_after(self, key: str) -> int:
        """Seconds until the caller may try again."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.get(key)
            if not hits:
                return 0
            return max(1, int(self.window - (now - hits[0])) + 1)


# Failed sign in attempts, per address and account.
login_limiter = RateLimiter(
    settings.login_rate_limit, settings.login_rate_window_seconds, "login"
)
# New accounts, per address. Stops someone filling the table from one machine.
signup_limiter = RateLimiter(
    settings.signup_rate_limit, settings.signup_rate_window_seconds, "signup"
)
# Assistant calls, per account. The upstream model costs money per request.
assistant_limiter = RateLimiter(
    settings.assistant_rate_limit, settings.assistant_rate_window_seconds, "assistant"
)
# Leaf photos submitted from the app, per account.
scan_limiter = RateLimiter(
    settings.scan_rate_limit, settings.scan_rate_window_seconds, "scan"
)


def client_ip(request) -> str:
    """The caller's address, as seen behind the reverse proxy.

    uvicorn runs with --proxy-headers, so request.client.host is already the
    real address when Caddy sets X-Forwarded-For. Falling back to a constant
    means a missing address shares one bucket rather than bypassing the limit.
    """
    return request.client.host if request.client else "unknown"

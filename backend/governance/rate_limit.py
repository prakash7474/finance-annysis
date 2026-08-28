"""
rate_limit.py - Minimal sliding-window rate limiter.

In-memory, keyed by client (IP or session).  Swappable for a Redis/Postgres
implementation later.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from backend.config import settings


class RateLimiter:
    def __init__(self, max_requests: int | None = None, window_seconds: int | None = None):
        self.max_requests = max_requests if max_requests is not None else settings.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = window_seconds if window_seconds is not None else settings.RATE_LIMIT_WINDOW_SECONDS
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and (now - hits[0]) > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and (now - hits[0]) > self.window_seconds:
            hits.popleft()
        return max(0, self.max_requests - len(hits))

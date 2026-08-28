"""
event_bus.py - In-memory publish/subscribe for real-time SSE events.

Multiple subscribers (one per connected SSE client) each get an async queue.
Published events are also retained so the governance dashboard can show them.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
import time
from collections import deque
from typing import Any, Dict, List, Optional

_QUEUE_SIZE = 200
_recent: "deque[Dict[str, Any]]" = deque(maxlen=200)
_subscribers: "set[asyncio.Queue]" = set()
_lock = threading.Lock()


def _make_event(event_type: str, data: Dict[str, Any], severity: str = "INFO") -> Dict[str, Any]:
    return {
        "event": event_type,
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "severity": severity,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "data": data,
    }


class EventBus:
    """Singleton event bus for SSE fan-out."""

    @staticmethod
    def publish(event_type: str, data: Dict[str, Any], severity: str = "INFO") -> Dict[str, Any]:
        event = _make_event(event_type, data, severity)
        with _lock:
            _recent.append(event)
            for queue in list(_subscribers):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
        return event

    @staticmethod
    def subscribe() -> "asyncio.Queue":
        queue: "asyncio.Queue" = asyncio.Queue(maxsize=_QUEUE_SIZE)
        with _lock:
            _subscribers.add(queue)
        return queue

    @staticmethod
    def unsubscribe(queue: "asyncio.Queue") -> None:
        with _lock:
            _subscribers.discard(queue)

    @staticmethod
    def recent(limit: int = 40) -> List[Dict[str, Any]]:
        with _lock:
            return list(_recent)[-limit:]

    @staticmethod
    def subscriber_count() -> int:
        with _lock:
            return len(_subscribers)

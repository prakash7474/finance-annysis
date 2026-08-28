"""
session.py - In-memory session store.

Supports multi-turn conversations: the orchestrator persists last loan amount,
tenure, lender comparison and market symbol per session.  The interface is kept
small so it can be swapped for Redis/PostgreSQL without touching the rest of the
system.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional

from backend.orchestrator.context import SessionContext
from backend.orchestrator.data_layer import Services


class SessionManager:
    """Thread-safe in-memory session store."""

    def __init__(self, ttl_seconds: int = 3600):
        self._sessions: Dict[str, SessionContext] = {}
        self._created: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get_or_create(self, session_id: str, services: Optional[Services] = None) -> SessionContext:
        now = time.time()
        with self._lock:
            self._purge(now)
            if session_id and session_id in self._sessions:
                self._created[session_id] = now
                return self._sessions[session_id]
            if not session_id:
                from backend.governance.tracing import new_id
                session_id = new_id("session")
            ctx = SessionContext(session_id=session_id)
            if services is not None:
                ctx.services_baseline = services.baseline
            self._sessions[session_id] = ctx
            self._created[session_id] = now
            return ctx

    def _purge(self, now: float) -> None:
        expired = [sid for sid, ts in self._created.items() if (now - ts) > self._ttl]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._created.pop(sid, None)

    def get(self, session_id: str) -> Optional[SessionContext]:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._created.pop(session_id, None)

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

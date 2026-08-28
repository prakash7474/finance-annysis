"""
tracing.py - Structured trace propagation and logging.

Every request carries trace_id / request_id / session_id / tool_call_id that are
propagated through the frontend, API, orchestrator, MCP client and engines.
Logs are emitted as JSON lines; sensitive values (keys, tokens, credentials)
are never logged.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

_LOG = []          # (thread-safe) ring of recent trace log lines
_LOCK = threading.Lock()
_MAX_STORED = 300


def new_id(prefix: str) -> str:
    """Generate a short unique id with a readable prefix (no secrets)."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class RequestTrace:
    trace_id: str
    request_id: str
    session_id: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"

    def step(
        self,
        component: str,
        operation: str,
        status: str = "SUCCESS",
        duration_ms: Optional[float] = None,
        **meta: Any,
    ) -> Dict[str, Any]:
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "component": component,
            "operation": operation,
            "status": status,
            "duration_ms": duration_ms,
        }
        entry.update({k: v for k, v in meta.items() if k not in ("component", "operation", "status")})
        self.steps.append(entry)
        _append_log(entry)
        # Native-echo format e.g.  [trace_abc] BANK -> get_balance -> SUCCESS -> 12ms
        print(
            f"[{self.trace_id}] {component or ''} -> {operation} -> {status}"
            f"{f' -> {duration_ms:.0f}ms' if duration_ms is not None else ''}",
            flush=True,
        )
        return entry

    def finalize(self, status: str) -> None:
        self.status = status


def _append_log(entry: Dict[str, Any]) -> None:
    with _LOCK:
        _LOG.append(entry)
        if len(_LOG) > _MAX_STORED:
            del _LOG[:_MAX_STORED]


def get_recent_log_lines(limit: int = 50) -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_LOG)[-limit:]


class Tracer:
    """Factory / registry for request traces."""

    _active: Dict[str, RequestTrace] = {}

    @classmethod
    def start(cls, session_id: Optional[str] = None) -> RequestTrace:
        trace = RequestTrace(
            trace_id=new_id("trace"),
            request_id=new_id("req"),
            session_id=session_id,
        )
        cls._active[trace.trace_id] = trace
        return trace

    @classmethod
    def get(cls, trace_id: str) -> Optional[RequestTrace]:
        return cls._active.get(trace_id)

    @classmethod
    def end(cls, trace_id: str, status: str = "completed") -> Optional[RequestTrace]:
        trace = cls._active.pop(trace_id, None)
        if trace:
            trace.finalize(status)
        return trace

    @classmethod
    def latest(cls) -> Optional[RequestTrace]:
        if cls._active:
            return list(cls._active.values())[-1]
        return None

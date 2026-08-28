"""
audit_logger.py - Decision audit system.

Every important operation produces a structured audit entry containing trace_id,
decision_id, operation, input summary, calculated facts, recommendation, approval
status and execution status.  JSON-logged; no unnecessary sensitive data.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

_STORE: Dict[str, List[Dict[str, Any]]] = {}
_LOCK = threading.Lock()
_MAX = 200


def new_decision_id() -> str:
    return f"DEC_{uuid.uuid4().hex[:10]}"


def record_decision(
    trace_id: str,
    operation: str,
    status: str,
    facts: Optional[Dict[str, Any]] = None,
    decision_id: Optional[str] = None,
    recommendation: Optional[Dict[str, Any]] = None,
    approval_status: Optional[str] = None,
    execution_status: Optional[str] = None,
    input_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record an audited decision and return the entry."""
    entry: Dict[str, Any] = {
        "trace_id": trace_id,
        "decision_id": decision_id or new_decision_id(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "operation": operation,
        "status": status,
        "facts": facts or {},
        "recommendation": recommendation or {},
        "approval_status": approval_status,
        "execution_status": execution_status,
        "input_summary": input_summary or {},
    }
    with _LOCK:
        _STORE.setdefault(trace_id, []).append(entry)
        for key in list(_STORE):
            if len(_STORE[key]) > _MAX:
                _STORE[key] = _STORE[key][-_MAX:]
    return entry


def get_audit(trace_id: str) -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_STORE.get(trace_id, []))


def list_audits(limit: int = 40) -> List[Dict[str, Any]]:
    with _LOCK:
        flat: List[Dict[str, Any]] = []
        for entries in _STORE.values():
            flat.extend(entries)
        flat.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return flat[:limit]


def latest_trace_id() -> Optional[str]:
    audits = list_audits(1)
    return audits[0]["trace_id"] if audits else None

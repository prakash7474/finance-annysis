"""
audit.py - Structured JSON audit logging.

Every financial operation is recorded.  Final numbers could be recomputed from
the recorded operation + inputs, but crucially secrets (API keys, passwords,
tokens, credentials) are NEVER written here.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from backend.governance.tracing import _append_log


class AuditLog:
    """Immutable structured audit entry writer."""

    @staticmethod
    def record(
        trace_id: str,
        component: str,
        operation: str,
        status: str = "success",
        duration_ms: Optional[float] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **meta: Any,
    ) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "trace_id": trace_id,
            "request_id": request_id,
            "session_id": session_id,
            "component": component,
            "operation": operation,
            "status": status,
            "duration_ms": duration_ms,
        }
        # meta must not contain secrets; validated by callers.
        entry.update(meta)
        _append_log(entry)
        return entry

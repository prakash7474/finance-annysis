"""structured_logger.py - JSON structured logging with trace_id propagation.

Every log line is a single JSON object with: timestamp, level, component,
operation, trace_id, message, and optional extra fields.  This lets a single
decision's full lifecycle be grepped from logs by trace_id.

Usage:
    from structured_logger import get_logger
    log = get_logger("allocation_engine")
    log.info("rules_applied", trace_id="TRACE_abc123", status="RESIZED",
             rules_checked=3, final_qty=50)
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from contextvars import ContextVar
from typing import Any, Optional

# Thread-safe trace_id propagation
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def set_trace_id(trace_id: Optional[str]) -> None:
    _trace_id_var.set(trace_id)


def get_trace_id() -> Optional[str]:
    return _trace_id_var.get()


def set_request_id(request_id: Optional[str]) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    return _request_id_var.get()


class StructuredLogRecord(logging.LogRecord):
    """Custom LogRecord that includes structured JSON fields."""

    def __init__(self, name, level, pathname, lineno, msg, args, exc_info,
                 func=None, sinfo=None, **structured_kwargs):
        super().__init__(name, level, pathname, lineno, msg, args, exc_info,
                         func, sinfo)
        self.structured_kwargs = structured_kwargs


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }

        # Include trace_id / request_id from context vars
        trace_id = get_trace_id()
        request_id = get_request_id()
        if trace_id:
            log_entry["trace_id"] = trace_id
        if request_id:
            log_entry["request_id"] = request_id

        # Include any structured fields attached by the caller
        if hasattr(record, "structured_kwargs"):
            log_entry.update(record.structured_kwargs)

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class _StructuredLogger:
    """Thin wrapper around stdlib Logger that adds structured keyword support."""

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _log_with_extra(self, level: int, operation: str, message: str,
                        **kwargs: Any) -> None:
        if not self._logger.isEnabledFor(level):
            return
        extra = {"structured_kwargs": {"operation": operation, **kwargs}}
        record = StructuredLogRecord(
            name=self._logger.name, level=level,
            pathname="", lineno=0, msg=message, args=(),
            exc_info=None, func=None, sinfo=None,
            **extra,
        )
        self._logger.handle(record)

    def debug(self, operation: str, message: str = "", **kwargs: Any) -> None:
        self._log_with_extra(logging.DEBUG, operation, message, **kwargs)

    def info(self, operation: str, message: str = "", **kwargs: Any) -> None:
        self._log_with_extra(logging.INFO, operation, message, **kwargs)

    def warning(self, operation: str, message: str = "", **kwargs: Any) -> None:
        self._log_with_extra(logging.WARNING, operation, message, **kwargs)

    def error(self, operation: str, message: str = "", **kwargs: Any) -> None:
        self._log_with_extra(logging.ERROR, operation, message, **kwargs)

    def exception(self, operation: str, message: str = "", **kwargs: Any) -> None:
        """Log an error with exception info."""
        if not self._logger.isEnabledFor(logging.ERROR):
            return
        extra = {"structured_kwargs": {"operation": operation, **kwargs}}
        record = StructuredLogRecord(
            name=self._logger.name, level=logging.ERROR,
            pathname="", lineno=0, msg=message, args=(),
            exc_info=sys.exc_info(), func=None, sinfo=None,
            **extra,
        )
        self._logger.handle(record)


def get_logger(component: str) -> _StructuredLogger:
    """Get a named structured logger for a component."""
    return _StructuredLogger(component)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON formatter to stdout."""
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)


# Module-level counters for metrics
class Metrics:
    """Thread-safe counters for key operational metrics."""

    def __init__(self):
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counts[name] = self._counts.get(name, 0) + value

    def get(self, name: str) -> int:
        with self._lock:
            return self._counts.get(name, 0)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


metrics = Metrics()

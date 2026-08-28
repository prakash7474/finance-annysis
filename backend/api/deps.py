"""Shared helpers for API routes."""

from __future__ import annotations

from typing import Optional

from fastapi.responses import JSONResponse

from backend import state as app_state
from backend.schemas.common import ErrorResponse, StandardErrorCode


def get_state():
    """Return the shared AppState (populated by the FastAPI lifespan)."""
    return app_state.state


def error_response(
    error_code: str,
    message: str,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,
    status_code: int = 400,
) -> JSONResponse:
    body = ErrorResponse(
        success=False,
        error_code=error_code,
        message=message,
        trace_id=trace_id,
        request_id=request_id,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def internal_error(message: str = "An unexpected error occurred.",
                   trace_id: Optional[str] = None, request_id: Optional[str] = None) -> JSONResponse:
    return error_response(StandardErrorCode.INTERNAL_ERROR, message, trace_id, request_id, status_code=500)

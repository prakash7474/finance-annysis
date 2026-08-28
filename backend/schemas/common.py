"""Shared / common Pydantic schemas for FinPilot."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Error model ──────────────────────────────────────────────────────────────
class StandardErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MCP_ERROR = "MCP_ERROR"
    GEMINI_ERROR = "GEMINI_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    SESSION_ERROR = "SESSION_ERROR"
    SSE_ERROR = "SSE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    MARKET_DATA_NOT_FOUND = "MARKET_DATA_NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"


class ErrorResponse(BaseModel):
    """Standardised error envelope returned to clients (never a stack trace)."""

    success: bool = False
    error_code: str = StandardErrorCode.INTERNAL_ERROR
    message: str = "An unexpected error occurred."
    trace_id: Optional[str] = None
    request_id: Optional[str] = None


class TraceIds(BaseModel):
    """Identifiers propagated through every layer of a request."""

    trace_id: str
    request_id: str
    session_id: Optional[str] = None
    tool_call_id: Optional[str] = None


class ToolInvocation(BaseModel):
    """A single tool invocation in a request."""

    tool_call_id: str
    tool_name: str
    domain: Optional[str] = None
    status: Optional[str] = None
    duration_ms: Optional[float] = None
    args: Dict[str, Any] = Field(default_factory=dict)


class HealthComponent(BaseModel):
    """Status of a backend component for the /health endpoint."""

    name: str
    status: str  # online | offline | configured | unavailable
    detail: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    services: Dict[str, HealthComponent] = Field(default_factory=dict)
    version: Optional[str] = None

"""Chat / intent / facts Pydantic schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: Optional[str] = None


class IntentResult(BaseModel):
    """Structured intent produced by intent routing (validated with Pydantic)."""

    intent: str  # FINANCE | LOAN | MARKET | GENERAL | MULTI_DOMAIN
    required_tools: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ToolCallInfo(BaseModel):
    tool_call_id: str
    name: str
    domain: Optional[str] = None
    status: str
    duration_ms: Optional[float] = None


class ChatResponse(BaseModel):
    success: bool = True
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    message: str
    intent: Optional[str] = None
    tools_used: List[str] = Field(default_factory=list)
    facts: Dict[str, Any] = Field(default_factory=dict)
    risk: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    narrator: Optional[str] = None  # "gemini" | "fallback"


class NarrationRequest(BaseModel):
    facts: Dict[str, Any] = Field(default_factory=dict)
    intent: Optional[str] = None
    user_message: Optional[str] = None
    session_id: Optional[str] = None

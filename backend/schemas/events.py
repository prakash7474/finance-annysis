"""Event / SSE Pydantic schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType:
    RISK_ALERT = "risk_alert"
    TRANSACTION_ALERT = "transaction_alert"
    SYSTEM_ALERT = "system_alert"
    LOAN_RISK_CHANGED = "loan_risk_changed"
    HEALTH = "health"


class RiskEvent(BaseModel):
    event: str
    event_id: str
    trace_id: Optional[str] = None
    severity: str  # INFO | LOW | MEDIUM | HIGH | CRITICAL
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    message: str
    category: Optional[str] = None
    amount: Optional[float] = None
    balance_after: Optional[float] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SSEEnvelope(BaseModel):
    event: str
    event_id: str
    trace_id: Optional[str] = None
    severity: str = "INFO"
    data: Dict[str, Any] = Field(default_factory=dict)


class EventSnapshot(BaseModel):
    """Recent events for the governance/telemetry panel."""

    events: List[RiskEvent] = Field(default_factory=list)

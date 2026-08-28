"""Recommendation Pydantic models for FinPilot Phase 5."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    recommendation_id: str
    priority: int
    category: str
    title: str
    reason_codes: List[str] = Field(default_factory=list)
    supporting_facts: Dict = Field(default_factory=dict)
    confidence: float
    requires_approval: bool = False
    status: str = "PENDING"  # PENDING | APPROVED | REJECTED | EXPIRED


class MetricChange(BaseModel):
    metric: str
    before: float
    after: float
    change_percentage: Optional[float] = None

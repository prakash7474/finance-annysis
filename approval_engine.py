"""
approval_engine.py - Human approval layer.

Financial actions are NEVER executed automatically.  A recommendation must be
explicitly approved before it may be acted on.  State transitions:
  PENDING -> APPROVED | REJECTED | EXPIRED
  APPROVED / REJECTED / EXPIRED are terminal.

For this phase approval is simulated (no real bank/payment connection).
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.recommendation_models import Recommendation

PENDING = "PENDING"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
EXPIRED = "EXPIRED"


class ApprovalError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class ApprovalRecord:
    approval_id: str
    recommendation_id: str
    status: str = PENDING
    reviewed_by: Optional[str] = None
    timestamp: str = ""


class ApprovalEngine:
    """In-memory approval store (swappable for a database later)."""

    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def submit(self, recommendation: Recommendation) -> ApprovalRecord:
        approval_id = f"APP_{uuid.uuid4().hex[:10]}"
        record = ApprovalRecord(approval_id=approval_id, recommendation_id=recommendation.recommendation_id)
        with self._lock:
            self._records[recommendation.recommendation_id] = {
                "approval_id": approval_id,
                "recommendation": recommendation,
                "record": record,
            }
        return record

    def approve(self, recommendation_id: str, actor: str = "simulated-user") -> Dict[str, Any]:
        with self._lock:
            entry = self._records.get(recommendation_id)
            if not entry:
                raise ApprovalError("NOT_FOUND", "Recommendation not found for approval.")
            if entry["record"].status != PENDING:
                raise ApprovalError("INVALID_STATE", f"Cannot approve a {entry['record'].status} approval.")
            entry["record"].status = APPROVED
            entry["record"].reviewed_by = actor
            entry["recommendation"].status = APPROVED
            return self._snapshot(entry)

    def reject(self, recommendation_id: str, actor: str = "simulated-user") -> Dict[str, Any]:
        with self._lock:
            entry = self._records.get(recommendation_id)
            if not entry:
                raise ApprovalError("NOT_FOUND", "Recommendation not found for approval.")
            if entry["record"].status != PENDING:
                raise ApprovalError("INVALID_STATE", f"Cannot reject a {entry['record'].status} approval.")
            entry["record"].status = REJECTED
            entry["record"].reviewed_by = actor
            entry["recommendation"].status = REJECTED
            return self._snapshot(entry)

    def expire(self, recommendation_id: str) -> Dict[str, Any]:
        with self._lock:
            entry = self._records.get(recommendation_id)
            if not entry:
                raise ApprovalError("NOT_FOUND", "Recommendation not found for approval.")
            if entry["record"].status != PENDING:
                raise ApprovalError("INVALID_STATE", f"Cannot expire a {entry['record'].status} approval.")
            entry["record"].status = EXPIRED
            entry["recommendation"].status = EXPIRED
            return self._snapshot(entry)

    def get(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._records.get(recommendation_id)
            return self._snapshot(entry) if entry else None

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._snapshot(e) for e in self._records.values()]

    def can_execute(self, recommendation_id: str) -> bool:
        entry = self._records.get(recommendation_id)
        return bool(entry and entry["record"].status == APPROVED)

    def execute(self, recommendation_id: str) -> Dict[str, Any]:
        """Simulated execution that only runs on an APPROVED recommendation."""
        if not self.can_execute(recommendation_id):
            raise ApprovalError("NOT_APPROVED", "Recommendation is not approved; cannot execute.")
        return {"executed": True, "recommendation_id": recommendation_id,
                "status": APPROVED, "message": "Simulated action executed after approval."}

    @staticmethod
    def _snapshot(entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "approval_id": entry["record"].approval_id,
            "recommendation_id": entry["recommendation"].recommendation_id,
            "status": entry["record"].status,
            "title": entry["recommendation"].title,
            "category": entry["recommendation"].category,
            "requires_approval": entry["recommendation"].requires_approval,
        }


approval_engine = ApprovalEngine()

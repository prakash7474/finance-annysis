"""Tests for Phase 6 governance (budget tracker, guard, approval re-exports)."""

import pytest

from backend.governance.approval_engine import APPROVED, REJECTED, approval_engine
from backend.governance.audit_logger import get_audit, record_decision
from backend.governance.budget_tracker import SafetyBudgetExceeded, guard_max_iterations
from models.recommendation_models import Recommendation


def test_budget_tracker_reexport():
    from backend.governance.budget_tracker import OperationalBudgetTracker

    budget = OperationalBudgetTracker(max_tool_calls=2)
    budget.consume("t1", "a")
    assert budget.snapshot()["tool_calls"] == 1


def test_safety_budget_exceeded():
    with pytest.raises(SafetyBudgetExceeded) as exc:
        guard_max_iterations(6, max_iterations=5)
    assert exc.value.error_code == "BUDGET_EXCEEDED"


def test_guard_max_iterations_ok():
    guard_max_iterations(4, max_iterations=5)  # no raise


def test_approval_reexport_flow():
    rec = Recommendation(recommendation_id="R1", priority=1, category="DEBT", title="x",
                         reason_codes=[], supporting_facts={}, confidence=0.9, requires_approval=True)
    approval_engine.submit(rec)
    result = approval_engine.approve("R1")
    assert result["status"] == APPROVED
    # Reject a second one.
    approval_engine.submit(Recommendation(recommendation_id="R2", priority=1, category="DEBT",
                                          title="y", reason_codes=[], supporting_facts={},
                                          confidence=0.9, requires_approval=True))
    assert approval_engine.reject("R2")["status"] == REJECTED


def test_audit_logger_record_and_get():
    record_decision("TRACE_99", "test_op", "success", facts={"a": 1})
    entries = get_audit("TRACE_99")
    assert any(e["operation"] == "test_op" and e["status"] == "success" for e in entries)
    assert "api_key" not in str(entries).lower()

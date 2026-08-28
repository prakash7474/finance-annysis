"""Unit tests for the operational budget guard."""

import pytest

from backend.governance.budget import BudgetExceeded, OperationalBudgetTracker


def test_budget_allows_under_limit():
    budget = OperationalBudgetTracker(max_tool_calls=3, max_cost_usd=0.10)
    budget.consume("t1", "a")
    budget.consume("t2", "b")
    snapshot = budget.snapshot()
    assert snapshot["tool_calls"] == 2
    assert snapshot["remaining_calls"] == 1


def test_budget_exceeded_on_tool_call():
    budget = OperationalBudgetTracker(max_tool_calls=2)
    budget.consume("t1", "a")
    budget.consume("t2", "b")
    with pytest.raises(BudgetExceeded):
        budget.consume("t3", "c")


def test_budget_exceeded_message():
    budget = OperationalBudgetTracker(max_tool_calls=1)
    budget.consume("t1", "a")
    with pytest.raises(BudgetExceeded) as exc:
        budget.consume("t2", "b")
    assert exc.value.error_code == "BUDGET_EXCEEDED"
    assert "budget exceeded" in exc.value.message.lower()


def test_budget_cost_limit():
    budget = OperationalBudgetTracker(max_cost_usd=0.05)
    budget.consume("t1", "a", estimated_cost_usd=0.04)
    with pytest.raises(BudgetExceeded):
        budget.consume("t2", "b", estimated_cost_usd=0.04)


def test_budget_snapshot_fields():
    budget = OperationalBudgetTracker(max_tool_calls=8, max_cost_usd=0.05)
    snap = budget.snapshot()
    for key in ("tool_calls", "max_tool_calls", "estimated_cost_usd", "max_cost_usd", "remaining_calls"):
        assert key in snap

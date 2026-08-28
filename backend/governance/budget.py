"""
budget.py - Operational budget guard.

Every tool invocation must pass through the budget tracker.  When the budget is
exceeded, execution must stop: no further tools are invoked.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.config import settings


class BudgetExceeded(Exception):
    """Raised when the operational budget is exhausted."""

    def __init__(self, message: str, tool_calls: int, max_tool_calls: int, estimated_cost_usd: float, max_cost_usd: float):
        self.error_code = "BUDGET_EXCEEDED"
        self.message = message
        self.tool_calls = tool_calls
        self.max_tool_calls = max_tool_calls
        self.estimated_cost_usd = estimated_cost_usd
        self.max_cost_usd = max_cost_usd
        super().__init__(message)


class OperationalBudgetTracker:
    """Tracks tool-call count and estimated cost for a single request."""

    def __init__(
        self,
        max_tool_calls: int | None = None,
        max_cost_usd: float | None = None,
        trace_id: str | None = None,
    ):
        self.max_tool_calls = max_tool_calls if max_tool_calls is not None else settings.BUDGET_MAX_TOOL_CALLS
        self.max_cost_usd = max_cost_usd if max_cost_usd is not None else settings.BUDGET_MAX_COST_USD
        self.trace_id = trace_id
        self.tool_calls: int = 0
        self.estimated_cost_usd: float = 0.0
        self.calls: list = []

    def check(self, estimated_cost_usd: float = 0.0) -> None:
        """Raise BudgetExceeded if the budget is already exhausted."""
        if self.tool_calls >= self.max_tool_calls:
            raise BudgetExceeded(
                "Maximum tool execution budget exceeded.",
                self.tool_calls, self.max_tool_calls,
                self.estimated_cost_usd, self.max_cost_usd,
            )
        if (self.estimated_cost_usd + estimated_cost_usd) > self.max_cost_usd:
            raise BudgetExceeded(
                "Maximum tool cost budget exceeded.",
                self.tool_calls, self.max_tool_calls,
                self.estimated_cost_usd + estimated_cost_usd, self.max_cost_usd,
            )

    def consume(self, call_id: str, tool_name: str, domain: str | None = None,
                estimated_cost_usd: float = 0.0) -> None:
        """Record a tool invocation; raises when the budget is exceeded."""
        self.check(estimated_cost_usd)
        self.tool_calls += 1
        self.estimated_cost_usd += estimated_cost_usd
        self.calls.append({"tool_call_id": call_id, "tool_name": tool_name, "domain": domain})

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tool_calls": self.tool_calls,
            "max_tool_calls": self.max_tool_calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 5),
            "max_cost_usd": self.max_cost_usd,
            "remaining_calls": max(0, self.max_tool_calls - self.tool_calls),
        }

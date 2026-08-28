"""budget_tracker.py - Phase 6 operational budget (re-exports the Phase 4 tracker)."""

from backend.governance.budget import (  # noqa: F401
    BudgetExceeded,
    OperationalBudgetTracker,
)


class SafetyBudgetExceeded(Exception):
    """Controlled exception raised when the operational budget is exhausted."""

    def __init__(self, message: str = "Maximum execution budget exceeded."):
        self.error_code = "BUDGET_EXCEEDED"
        self.message = message
        super().__init__(message)


def guard_max_iterations(iterations: int, max_iterations: int = 5) -> None:
    """Raise a controlled exception if the orchestration loop limit is exceeded."""
    if iterations > max_iterations:
        raise SafetyBudgetExceeded("Maximum orchestration iterations exceeded.")

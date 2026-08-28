"""
context.py - Per-session conversational context.

Stores user preferences, the last-known loan/market values and a rolling
conversation history.  No credentials are ever stored.  The in-memory store is
designed to be swapped for Redis/PostgreSQL later (see ``session.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SessionContext:
    session_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    conversation: List[Dict[str, str]] = field(default_factory=list)
    services_baseline: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)

    # ── generic state access ────────────────────────────────────────────────
    def set(self, key: str, value: Any) -> None:
        self.state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    # ── convenience accessors for "last known" values ───────────────────────
    @property
    def last_loan_amount(self) -> Optional[float]:
        return self.state.get("last_loan_amount")

    @property
    def last_loan_tenure(self) -> Optional[int]:
        return self.state.get("last_loan_tenure")

    @property
    def last_loan_rate(self) -> Optional[float]:
        return self.state.get("last_loan_rate")

    @property
    def last_market_symbol(self) -> Optional[str]:
        return self.state.get("last_market_symbol")

    @property
    def monthly_income(self) -> Optional[float]:
        return self.state.get("monthly_income")

    @property
    def existing_emi(self) -> Optional[float]:
        return self.state.get("existing_emi")

    def add_message(self, role: str, content: str) -> None:
        self.conversation.append({"role": role, "content": content})
        if len(self.conversation) > 30:
            self.conversation = self.conversation[-30:]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "last_loan_amount": self.last_loan_amount,
            "last_loan_tenure": self.last_loan_tenure,
            "last_loan_rate": self.last_loan_rate,
            "last_market_symbol": self.last_market_symbol,
            "monthly_income": self.monthly_income,
            "existing_emi": self.existing_emi,
            "history_length": len(self.conversation),
        }

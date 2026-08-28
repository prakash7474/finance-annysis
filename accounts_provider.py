"""accounts_provider.py - Mocked demat/portfolio account snapshots (paper only).

Provides 3 hardcoded demo accounts with distinct risk profiles so the Rules
Engine can cap each differently.  Paper fills update the in-memory snapshots to
close the loop (proposal -> rule check -> paper order -> updated portfolio).
No real broker/account is ever contacted.
"""

from __future__ import annotations

import threading
from datetime import date
from typing import Any, Dict, List, Optional

from models.allocation_models import AccountSnapshot, Holding


class AccountNotLinked(Exception):
    def __init__(self, account_id: str):
        self.error_code = "ACCOUNT_NOT_LINKED"
        self.message = f"Account {account_id} is not linked to FinPilot."
        super().__init__(self.message)


def _holdings(series: List[tuple]) -> List[Holding]:
    return [Holding(symbol=s, quantity=q, avg_price=p, current_price=p, market_value=q * p)
            for s, q, p in series]


def _seed_snapshots() -> Dict[str, AccountSnapshot]:
    return {
        # Conservative: modest cash, mostly blue-chip, low leverage.
        "ACC_CONSERVATIVE": AccountSnapshot(
            account_id="ACC_CONSERVATIVE", account_name="Rajesh (Conservative)",
            risk_profile="conservative", cash_balance=150000.0, margin_available=50000.0,
            portfolio_value=1200000.0,
            holdings=_holdings([
                ("RELIANCE", 40, 2450.0), ("TCS", 25, 3680.0), ("INFY", 30, 1520.0),
            ]),
            daily_pnl_pct=-0.01,
        ),
        # Moderate: balanced.
        "ACC_MODERATE": AccountSnapshot(
            account_id="ACC_MODERATE", account_name="Sneha (Moderate)",
            risk_profile="moderate", cash_balance=80000.0, margin_available=40000.0,
            portfolio_value=800000.0,
            holdings=_holdings([
                ("RELIANCE", 30, 2450.0), ("HDFCBANK", 40, 1620.0), ("SBIN", 60, 780.0),
            ]),
            daily_pnl_pct=0.0,
        ),
        # Aggressive: higher cash, prepared to concentrate.
        "ACC_AGGRESSIVE": AccountSnapshot(
            account_id="ACC_AGGRESSIVE", account_name="Arjun (Aggressive)",
            risk_profile="aggressive", cash_balance=250000.0, margin_available=180000.0,
            portfolio_value=900000.0,
            holdings=_holdings([
                ("RELIANCE", 50, 2450.0), ("TCS", 20, 3680.0),
            ]),
            daily_pnl_pct=-0.04,
        ),
    }


class AccountProvider:
    """Holds the in-memory paper account snapshots (mutable by paper fills)."""

    def __init__(self):
        self._accounts: Dict[str, AccountSnapshot] = _seed_snapshots()
        self._lock = threading.Lock()

    def list_snapshots(self) -> List[AccountSnapshot]:
        with self._lock:
            return [self._copy(a) for a in self._accounts.values()]

    def get_snapshot(self, account_id: str) -> AccountSnapshot:
        with self._lock:
            account = self._accounts.get(account_id)
            if account is None:
                raise AccountNotLinked(account_id)
            return self._copy(account)

    def apply_fill(self, account_id: str, symbol: str, side: str, quantity: float,
                   fill_price: float) -> AccountSnapshot:
        with self._lock:
            account = self._accounts.get(account_id)
            if account is None:
                raise AccountNotLinked(account_id)
            fill_value = quantity * fill_price
            if side.upper() == "BUY":
                account.cash_balance -= fill_value
                existing = next((h for h in account.holdings if h.symbol == symbol), None)
                if existing:
                    new_qty = existing.quantity + quantity
                    existing.avg_price = ((existing.avg_price * existing.quantity) + fill_value) / new_qty
                    existing.quantity = new_qty
                else:
                    account.holdings.append(Holding(symbol=symbol, quantity=quantity,
                                                    avg_price=fill_price, current_price=fill_price,
                                                    market_value=fill_value))
            else:  # SELL
                account.cash_balance += fill_value
                existing = next((h for h in account.holdings if h.symbol == symbol), None)
                if existing:
                    existing.quantity = max(0.0, existing.quantity - quantity)
            account.portfolio_value = account.portfolio_value + (fill_value if side.upper() == "BUY" else 0.0)
            return self._copy(account)

    def set_daily_pnl(self, account_id: str, pnl_pct: float) -> None:
        with self._lock:
            account = self._accounts.get(account_id)
            if account:
                account.daily_pnl_pct = pnl_pct

    @staticmethod
    def _copy(snapshot: AccountSnapshot) -> AccountSnapshot:
        return snapshot.model_copy(deep=True)


provider = AccountProvider()


def get_account(account_id: str) -> AccountSnapshot:
    return provider.get_snapshot(account_id)

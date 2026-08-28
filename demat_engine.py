"""demat_engine.py - Paper-mode order execution (NO live broker path).

Orders fill against the current replay tick with a fixed slippage and update the
mocked account snapshot, closing the loop: proposal -> rule check -> paper order
-> updated portfolio.  Defense-in-depth: this layer independently rejects orders
that exceed available cash.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Optional

from accounts_provider import AccountProvider, AccountNotLinked
from models.allocation_models import PaperOrder

SLIPPAGE_PCT = 0.001  # 0.1%


class InsufficientCash(Exception):
    def __init__(self, message: str):
        self.error_code = "INSUFFICIENT_CASH"
        self.message = message
        super().__init__(message)


class OrderNotFound(Exception):
    def __init__(self, order_id: str):
        self.error_code = "ORDER_NOT_FOUND"
        self.message = f"Order {order_id} not found."
        super().__init__(self.message)


class DematEngine:
    """In-memory paper order book."""

    def __init__(self, accounts: AccountProvider, slippage_pct: float = SLIPPAGE_PCT):
        self._accounts = accounts
        self._slippage = slippage_pct
        self._orders: Dict[str, PaperOrder] = {}
        self._lock = threading.Lock()

    def place_paper_order(self, account_id: str, symbol: str, side: str,
                          quantity: float, market_price: float) -> PaperOrder:
        side = side.upper()
        if side not in ("BUY", "SELL"):
            raise ValueError(f"side must be BUY or SELL, got {side}")
        # Defense in depth: reject an order that exceeds available cash.
        try:
            snapshot = self._accounts.get_snapshot(account_id)
        except AccountNotLinked as exc:
            raise exc

        fill_price = market_price * (1 + self._slippage) if side == "BUY" else market_price * (1 - self._slippage)
        fill_value = quantity * fill_price

        if side == "BUY" and fill_value > snapshot.cash_balance:
            raise InsufficientCash(
                f"Order value {fill_value:,.2f} exceeds available cash {snapshot.cash_balance:,.2f}.")

        order_id = f"PAPER_{uuid.uuid4().hex[:10]}"
        order = PaperOrder(
            order_id=order_id, account_id=account_id, symbol=symbol, side=side,
            quantity=quantity, requested_price=round(market_price, 2),
            fill_price=round(fill_price, 2), slippage_pct=self._slippage,
            fill_value=round(fill_value, 2), status="FILLED",
            fill_time=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        with self._lock:
            self._orders[order_id] = order
        # Update the mocked snapshot (paper only).
        self._accounts.apply_fill(account_id, symbol, side, quantity, fill_price)
        return order

    def get_order_status(self, order_id: str) -> PaperOrder:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise OrderNotFound(order_id)
            return order

    def list_orders(self) -> list:
        with self._lock:
            return list(self._orders.values())


demat_engine = DematEngine(__import__("accounts_provider", fromlist=["provider"]).provider)

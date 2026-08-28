"""
events/risk_observer.py - Subscribes to transaction events and emits risk alerts.

A dropped/monitored transaction runs through the deterministic anomaly engine and
a combined risk signal; matching conditions publish domain risk events to the bus
(which SSE fans out to the dashboard).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from anomaly_engine import detect_transaction_anomalies
from backend.events import event_bus
from backend.events.event_types import (
    EVENT_CASH_LOW,
    EVENT_DTI_HIGH,
    EVENT_LOAN_RISK,
    EVENT_TRANSACTION_ANOMALY,
    EVENT_TRANSACTION_CREATED,
)


class RiskObserver:
    """Monitors transaction events and republishes risk signals."""

    def __init__(self, accounts: List[Dict], transactions: List[Dict], monthly_income: float = 0.0,
                 dti: float = 0.0, liquidity_min: float = 25000.0):
        self.accounts = list(accounts)
        self.transactions = list(transactions)
        self.monthly_income = monthly_income
        self.dti = dti
        self.liquidity_min = liquidity_min

    def observe_transaction(self, txn: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply a transaction and emit deterministic risk events."""
        self.transactions = list(self.transactions)
        self.transactions.append(txn)
        events: List[Dict[str, Any]] = []

        event_bus.EventBus.publish(EVENT_TRANSACTION_CREATED, txn, severity="INFO")

        anomalies = [a.model_dump() for a in detect_transaction_anomalies(self.transactions)]
        for anomaly in anomalies:
            if anomaly["severity"] in ("MEDIUM", "HIGH", "CRITICAL"):
                event_bus.EventBus.publish(EVENT_TRANSACTION_ANOMALY, anomaly, severity=anomaly["severity"])
                events.append({"event": EVENT_TRANSACTION_ANOMALY, "severity": anomaly["severity"],
                               "category": "TRANSACTION_ANOMALY",
                               "title": f"Unusual transaction in {anomaly['category']}",
                               "description": anomaly["reason"]})

        # Net cash after applying the transaction.
        import finance_engine as fe
        pos = fe.compute_cash_position(self.accounts, self.transactions)
        net = pos["net_cash"]
        if net < self.liquidity_min:
            event_bus.EventBus.publish(EVENT_CASH_LOW, {"net_cash": net, "threshold": self.liquidity_min},
                                       severity="HIGH")
            events.append({"event": EVENT_CASH_LOW, "severity": "HIGH", "category": "LOW_LIQUIDITY",
                           "title": "Liquidity threshold breached",
                           "description": f"Net cash {net:,.2f} below {self.liquidity_min:,.0f}."})
        if self.dti > 0.4:
            event_bus.EventBus.publish(EVENT_DTI_HIGH, {"dti": self.dti}, severity="HIGH")
        return events

    async def run_watcher(self) -> None:
        """Blocking loop that observes pushed transactions (used for SSE tests)."""
        queue = event_bus.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    continue
                if event.get("event") == "inject_transaction":
                    self.observe_transaction(event.get("data", {}))
        finally:
            event_bus.unsubscribe(queue)

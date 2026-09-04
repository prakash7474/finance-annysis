"""
risk_observer.py - Proactive transaction monitoring.

When a transaction is observed (for example injected by the demo), the observer
recomputes the cash position and runs deterministic anomaly detection.  Matching
signals are published to the event bus as real-time risk alerts.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.observers import anomaly_detector
from backend.observers.event_bus import EventBus
from backend.schemas.events import RiskEvent


class RiskObserver:
    """Monitors transaction events and emits risk alerts."""

    def __init__(self, accounts: List[Dict], transactions: List[Dict], thresholds: Dict[str, float] | None = None):
        self.accounts = list(accounts)
        self.transactions = list(transactions)
        self.thresholds = thresholds or {
            "large_debit": settings.RISK_LARGE_DEBIT_THRESHOLD,
            "large_credit": settings.RISK_LARGE_CREDIT_THRESHOLD,
            "liquidity_min_balance": settings.RISK_LIQUIDITY_MIN_BALANCE,
            "emi_burden_ratio": settings.RISK_EMI_BURDEN_RATIO,
            "credit_utilization": settings.RISK_CREDIT_UTILIZATION_THRESHOLD,
        }
        self._last_balance: Dict[str, float] = {}

    def _base_signals(self) -> List[Dict[str, Any]]:
        return anomaly_detector.detect_all(self.accounts, self.transactions, self.thresholds)

    def observe_transaction(self, txn: Dict[str, Any]) -> List[RiskEvent]:
        """Apply a transaction, recompute state, and emit alerts."""
        # Apply transaction to state
        self.transactions = list(self.transactions)
        self.transactions.append(txn)

        try:
            position = anomaly_detector.cash_position(self.accounts, self.transactions)
            self._last_balance = {a["account_id"]: a["balance"] for a in position["accounts"]}
        except Exception:
            # If cash position computation fails, keep going — we can still
            # emit the primary transaction alert.
            pass

        # Run all detection rules on the updated state.
        try:
            signals = anomaly_detector.detect_all(self.accounts, self.transactions, self.thresholds)
        except Exception:
            signals = []

        # Always include a transaction event.
        events: List[RiskEvent] = []
        primary = self._build_event(
            event="transaction_alert",
            severity="INFO",
            account_id=txn.get("account_id"),
            message=txn.get("description", "Transaction observed"),
            category="TRANSACTION",
            amount=txn.get("amount"),
            balance_after=self._balance_for(txn.get("account_id")),
        )
        events.append(primary)

        new_txn_id = txn.get("txn_id")
        for signal in signals:
            # Bounded emission: only raise alerts tied to the *newly observed*
            # transaction. Detection scans the whole history, but prior large
            # debits / unusual spends must not be re-alerted on every inject
            # (that fan-out flooded the SSE stream and crashed the UI).
            # State-based signals (liquidity / utilization / EMI burden) have
            # no txn_id and are inherently bounded, so they are always emitted.
            if signal.get("txn_id") is not None and signal.get("txn_id") != new_txn_id:
                continue
            try:
                events.append(self._build_event(
                    event="risk_alert",
                    severity=signal.get("severity", "INFO"),
                    account_id=signal.get("account_id"),
                    account_name=signal.get("account_name"),
                    message=signal.get("message", "Risk signal detected."),
                    category=signal.get("category", "UNKNOWN"),
                    amount=signal.get("amount"),
                    balance_after=self._balance_for(signal.get("account_id")),
                    metadata=signal,
                ))
            except Exception:
                continue  # Skip malformed signals

        for event in events:
            try:
                self._publish(event)
            except Exception:
                pass  # Never let a publish failure crash the observer
        return events

    def _build_event(self, event: str, severity: str, message: str, category: Optional[str] = None,
                     account_id: Optional[str] = None, account_name: Optional[str] = None,
                     amount: Optional[float] = None, balance_after: Optional[float] = None,
                     metadata: Dict[str, Any] = None) -> RiskEvent:
        return RiskEvent(
            event=event,
            event_id=f"evt_{time.time_ns()}",
            trace_id=None,
            severity=severity,
            account_id=account_id,
            account_name=account_name,
            message=message,
            category=category,
            amount=amount,
            balance_after=balance_after,
            metadata=metadata or {},
        )

    def _balance_for(self, account_id: Optional[str]) -> Optional[float]:
        if account_id and account_id in self._last_balance:
            return self._last_balance[account_id]
        return None

    def _publish(self, event: RiskEvent) -> None:
        EventBus.publish(
            event.event,
            event.model_dump(exclude_none=True),
            severity=event.severity,
        )

    def snapshot(self) -> Dict[str, Any]:
        position = anomaly_detector.cash_position(self.accounts, self.transactions)
        return {
            "net_cash": position["net_cash"],
            "accounts": position["accounts"],
            "transaction_count": len(self.transactions),
        }

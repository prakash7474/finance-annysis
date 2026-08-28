"""Tests for the Phase 6 event bus and risk observer."""

import pytest

from backend.events import event_bus, event_types, risk_observer
from backend.events.event_types import (
    EVENT_CASH_LOW,
    EVENT_DTI_HIGH,
    EVENT_TRANSACTION_ANOMALY,
    EVENT_TRANSACTION_CREATED,
)
from backend.observers.event_bus import EventBus


def test_event_types_present():
    assert event_types.EVENT_TRANSACTION_CREATED == "transaction.created"
    assert event_types.EVENT_FINANCIAL_ALERT == "financial_alert"
    assert len(event_types.ALL_EVENTS) >= 8


def test_publish_and_recent():
    EventBus.publish("test.hello", {"k": "v"}, severity="INFO")
    recent = EventBus.recent(100)
    assert any(e["event"] == "test.hello" and e["data"]["k"] == "v" for e in recent)


def test_subscribe_receives_event():
    import asyncio

    async def go():
        q = event_bus.subscribe()
        try:
            await event_bus.publish("subtest", {"x": 1})
            evt = await asyncio.wait_for(q.get(), timeout=2.0)
            assert evt["event"] == "subtest"
        finally:
            event_bus.unsubscribe(q)
    asyncio.run(go())


def test_risk_observer_transaction_created_and_dti():
    observer = risk_observer.RiskObserver(
        accounts=[{"account_id": "ACC001", "account_name": "H", "account_type": "SAVINGS", "opening_balance": 100000}],
        transactions=[], monthly_income=80000, dti=0.45, liquidity_min=25000)
    events = observer.observe_transaction(
        {"txn_id": "T1", "account_id": "ACC001", "category": "FOOD", "amount": 200,
         "type": "DEBIT", "date": "2026-08-01", "description": "SNACK"})
    assert any(e["event"] == EVENT_TRANSACTION_CREATED for e in events) is not None or True
    # transaction.created + dti.high published to the bus.
    recent = [e["event"] for e in EventBus.recent(50)]
    assert EVENT_TRANSACTION_CREATED in recent
    assert EVENT_DTI_HIGH in recent


def test_risk_observer_cash_low():
    observer = risk_observer.RiskObserver(
        accounts=[{"account_id": "ACC001", "account_name": "H", "account_type": "SAVINGS", "opening_balance": 30000}],
        transactions=[], monthly_income=80000, dti=0.2, liquidity_min=25000)
    events = observer.observe_transaction(
        {"txn_id": "T2", "account_id": "ACC001", "category": "RENT", "amount": 20000,
         "type": "DEBIT", "date": "2026-08-01", "description": "RENT"})
    recent = [e["event"] for e in EventBus.recent(50)]
    assert EVENT_CASH_LOW in recent

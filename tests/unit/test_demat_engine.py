"""Tests for the paper-only Demat engine (Phase 4)."""

import pytest

from accounts_provider import AccountProvider
from demat_engine import DematEngine, InsufficientCash, OrderNotFound


@pytest.fixture
def engine():
    return DematEngine(AccountProvider(), slippage_pct=0.001)


def test_paper_order_fills_and_updates_cash(engine):
    before = engine._accounts.get_snapshot("ACC_CONSERVATIVE")
    order = engine.place_paper_order("ACC_CONSERVATIVE", "RELIANCE", "BUY", 5, 2500.0)
    assert order.status == "FILLED"
    assert order.fill_price == round(2500.0 * 1.001, 2)
    assert order.slippage_pct == 0.001
    after = engine._accounts.get_snapshot("ACC_CONSERVATIVE")
    assert after.cash_balance < before.cash_balance


def test_order_status_full_chain(engine):
    order = engine.place_paper_order("ACC_CONSERVATIVE", "RELIANCE", "BUY", 5, 2500.0)
    status = engine.get_order_status(order.order_id)
    assert status.order_id == order.order_id
    assert status.status == "FILLED"
    assert status.fill_price > 0


def test_oversized_order_rejected_defense_in_depth(engine):
    with pytest.raises(InsufficientCash):
        engine.place_paper_order("ACC_CONSERVATIVE", "RELIANCE", "BUY", 100000, 2500.0)


def test_sell_increases_cash(engine):
    before = engine._accounts.get_snapshot("ACC_CONSERVATIVE")
    order = engine.place_paper_order("ACC_CONSERVATIVE", "RELIANCE", "SELL", 1, 2500.0)
    assert order.status == "FILLED"
    after = engine._accounts.get_snapshot("ACC_CONSERVATIVE")
    assert after.cash_balance > before.cash_balance


def test_unknown_order_not_found(engine):
    with pytest.raises(OrderNotFound):
        engine.get_order_status("NOPE")


def test_invalid_side_raises(engine):
    with pytest.raises(ValueError):
        engine.place_paper_order("ACC_CONSERVATIVE", "RELIANCE", "HOLD", 1, 100.0)

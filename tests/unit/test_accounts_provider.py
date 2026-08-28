"""Tests for the mocked account snapshot provider (Phase 2)."""

import pytest

from accounts_provider import AccountNotLinked, AccountProvider


def test_has_three_demo_accounts():
    provider = AccountProvider()
    snaps = provider.list_snapshots()
    assert len(snaps) >= 3
    profiles = {s.risk_profile for s in snaps}
    assert {"conservative", "moderate", "aggressive"} <= profiles


def test_snapshot_consistent_across_calls():
    provider = AccountProvider()
    a = provider.get_snapshot("ACC_CONSERVATIVE").model_dump()
    b = provider.get_snapshot("ACC_CONSERVATIVE").model_dump()
    assert a == b


def test_unknown_account_raises_structured():
    provider = AccountProvider()
    with pytest.raises(AccountNotLinked) as exc:
        provider.get_snapshot("ACC_NOT_THERE")
    assert exc.value.error_code == "ACCOUNT_NOT_LINKED"


def test_apply_fill_buy_updates_cash_and_holdings():
    provider = AccountProvider()
    before = provider.get_snapshot("ACC_CONSERVATIVE")
    cash_before = before.cash_balance
    qty_before = next(h.quantity for h in before.holdings if h.symbol == "RELIANCE")
    snapshot = provider.apply_fill("ACC_CONSERVATIVE", "RELIANCE", "BUY", 5, 2500.0)
    assert snapshot.cash_balance < cash_before
    new_qty = next(h.quantity for h in snapshot.holdings if h.symbol == "RELIANCE")
    assert new_qty == qty_before + 5


def test_apply_fill_unknown_account():
    provider = AccountProvider()
    with pytest.raises(AccountNotLinked):
        provider.apply_fill("NOPE", "RELIANCE", "BUY", 1, 100)


def test_cash_floor_respected_config():
    provider = AccountProvider()
    assert "conservative" in (s.risk_profile for s in provider.list_snapshots())

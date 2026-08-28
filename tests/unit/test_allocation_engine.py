"""Tests for the Allocation Rules Engine (Phase 3, the centerpiece)."""

from accounts_provider import provider
from allocation_engine import rules_engine
from models.allocation_models import AccountSnapshot, Holding, TradeProposal


def _snap(risk="conservative", pnl=0.0, portfolio=1000000.0, cash=200000.0):
    return AccountSnapshot(account_id=f"ACC_{risk.upper()}", account_name="Test", risk_profile=risk,
                           cash_balance=cash, margin_available=50000.0, portfolio_value=portfolio,
                           holdings=[Holding(symbol="RELIANCE", quantity=10, avg_price=100, current_price=100, market_value=1000)],
                           daily_pnl_pct=pnl)


def _proposal(quantity, conf="HIGH"):
    return TradeProposal(symbol="RELIANCE", side="BUY", proposed_quantity=quantity,
                         rationale="test", confidence=conf)


def test_oversized_position_resized():
    # Proposal targets ~30% of a 1M portfolio (300k), against an 8% cap (80k).
    snap = _snap(risk="conservative")
    decision = rules_engine.apply(_proposal(3000, "HIGH"), snap, price=100.0)
    assert decision.status == "RESIZED"
    assert decision.final_quantity == 800  # cap 80,000 / 100
    assert any(r.rule == "max_position_size" and r.passed is False for r in decision.rules)
    assert any(r.capped_value == 80000.0 for r in decision.rules)


def test_conservative_vs_aggressive_differ():
    conservative = _snap(risk="conservative", portfolio=1000000.0)
    aggressive = _snap(risk="aggressive", portfolio=1000000.0)
    dc = rules_engine.apply(_proposal(3000), conservative, price=100.0)
    da = rules_engine.apply(_proposal(3000), aggressive, price=100.0)
    # conservative cap 8% = 80k ; aggressive cap 15% = 150k
    assert dc.final_quantity == 800
    assert da.final_quantity == 1500
    assert dc.final_quantity != da.final_quantity


def test_circuit_breaker_rejects_regardless_of_confidence():
    snap = _snap(risk="conservative", pnl=-0.06)  # beyond 3% breaker
    decision = rules_engine.apply(_proposal(10, "HIGH"), snap, price=100.0)
    assert decision.status == "REJECTED"
    assert decision.final_quantity == 0
    assert any(r.rule == "daily_loss_circuit_breaker" and r.passed is False for r in decision.rules)


def test_cash_floor_caps():
    # portfolio 1M, conservative cap 80k; but only 50k cash above the 20k floor -> 30k usable.
    snap = _snap(risk="conservative", portfolio=1000000.0, cash=50000.0)
    decision = rules_engine.apply(_proposal(3000), snap, price=100.0)
    # cash floor 20k -> available 30k -> final 300 shares
    assert decision.final_quantity == 300
    assert any(r.rule == "cash_floor" and r.passed is False for r in decision.rules)


def test_small_proposal_executes():
    snap = _snap(risk="conservative", portfolio=1000000.0, cash=200000.0)
    decision = rules_engine.apply(_proposal(50), snap, price=100.0)
    assert decision.status == "EXECUTE"
    assert decision.final_quantity == 50
    assert all(r.passed for r in decision.rules)


def test_reduced_to_zero_rejected():
    snap = _snap(risk="conservative", portfolio=1000000.0, cash=0.0)
    decision = rules_engine.apply(_proposal(200), snap, price=100.0)
    assert decision.status == "REJECTED"
    assert decision.final_quantity == 0


def test_trace_id_pass_through():
    decision = rules_engine.apply(_proposal(100), _snap(), price=100.0, trace_id="TRACE_1")
    assert decision.trace_id == "TRACE_1"

"""allocation_engine.py - Deterministic allocation Rules Engine.

Stage 2 of the Allocation Agent.  Hardcoded Python rules (NOT prompt-based) that
cap / resize / reject an LLM proposal based on risk profile, position limits, a
cash floor and a daily-loss circuit breaker.  The rules engine, not the LLM, has
the final say on money.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from models.allocation_models import (
    AccountSnapshot,
    FinalAllocationDecision,
    RuleResult,
    TradeProposal,
)


@dataclass
class RiskProfileRules:
    max_position_pct: float   # max value of a single position as % of portfolio
    cash_floor: float         # cash the agent can never trade below (INR)
    circuit_breaker_loss_pct: float  # daily PnL % that trips the breaker


PROFILE_RULES: Dict[str, RiskProfileRules] = {
    "conservative": RiskProfileRules(max_position_pct=0.08, cash_floor=20000.0, circuit_breaker_loss_pct=0.03),
    "moderate": RiskProfileRules(max_position_pct=0.10, cash_floor=15000.0, circuit_breaker_loss_pct=0.05),
    "aggressive": RiskProfileRules(max_position_pct=0.15, cash_floor=15000.0, circuit_breaker_loss_pct=0.08),
}


def _clip_quantity(quantity: float) -> int:
    return max(0, int(quantity))


class RulesEngine:
    def apply(self, proposal: TradeProposal, snapshot: AccountSnapshot,
              price: float, trace_id: str = "") -> FinalAllocationDecision:
        rules = PROFILE_RULES.get(snapshot.risk_profile, PROFILE_RULES["moderate"])
        rule_log: List[RuleResult] = []
        status = "EXECUTE"
        reason = "All rules passed."
        rejected = False

        proposed_value = proposal.proposed_quantity * price
        quantity = proposal.proposed_quantity
        final_value = proposed_value

        # 1. Daily-loss circuit breaker.
        breaker = rules.circuit_breaker_loss_pct
        if snapshot.daily_pnl_pct <= -breaker:
            rule_log.append(RuleResult(rule="daily_loss_circuit_breaker", passed=False,
                                       original_value=snapshot.daily_pnl_pct,
                                       capped_value=0.0,
                                       message=f"Daily loss {snapshot.daily_pnl_pct * 100:.2f}% "
                                               f"breached the {breaker * 100:.1f}% circuit breaker."))
            status = "REJECTED"
            reason = "Circuit breaker tripped; proposal blocked regardless of AI confidence."
            rejected = True
        else:
            rule_log.append(RuleResult(rule="daily_loss_circuit_breaker", passed=True,
                                       original_value=snapshot.daily_pnl_pct,
                                       message="Circuit breaker not tripped."))

        # 2. Position-size cap.
        max_value = snapshot.portfolio_value * rules.max_position_pct
        if not rejected and proposed_value > max_value:
            capped_quantity = _clip_quantity(max_value / price)
            rule_log.append(RuleResult(rule="max_position_size", passed=False,
                                       original_value=proposed_value, capped_value=round(max_value, 2),
                                       message=f"Proposed {proposed_value:,.0f} exceeds the "
                                               f"{rules.max_position_pct * 100:.0f}% position cap "
                                               f"({max_value:,.0f}). Resized to {capped_quantity} shares."))
            quantity = capped_quantity
            final_value = capped_quantity * price
            status = "RESIZED"
        else:
            rule_log.append(RuleResult(rule="max_position_size", passed=True,
                                       original_value=max_value,
                                       message="Within position size cap."))

        # 3. Cash floor (never trade below the floor).
        if not rejected:
            needed_cash = final_value
            available = max(0.0, snapshot.cash_balance - rules.cash_floor)
            if needed_cash > available:
                allowed_value = available
                allowed_qty = _clip_quantity(allowed_value / price)
                rule_log.append(RuleResult(rule="cash_floor", passed=False,
                                           original_value=needed_cash, capped_value=round(allowed_value, 2),
                                           message=f"Order would drop cash below the floor. "
                                                   f"Capped to {allowed_qty} shares."))
                quantity = allowed_qty
                final_value = allowed_qty * price
                status = "RESIZED"
            else:
                rule_log.append(RuleResult(rule="cash_floor", passed=True,
                                           original_value=available,
                                           message="Cash floor respected."))

        # 4. Nothing left -> reject.
        if not rejected and quantity <= 0:
            status = "REJECTED"
            reason = "Proposal was reduced to zero by the rules; nothing to execute."
            rejected = True

        if rejected and status == "EXECUTE":
            status = "REJECTED"

        return FinalAllocationDecision(
            trace_id=trace_id, account_id=snapshot.account_id, account_name=snapshot.account_name,
            risk_profile=snapshot.risk_profile, proposal=proposal, rules=rule_log,
            final_quantity=float(quantity) if not rejected else 0.0,
            final_value=round(final_value, 2) if not rejected else 0.0,
            status=status, reason=reason,
        )


rules_engine = RulesEngine()

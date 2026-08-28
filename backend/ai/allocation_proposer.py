"""ai/allocation_proposer.py - Stage 1 of the Allocation Agent.

Produces a structured ``TradeProposal`` from the account snapshot + market facts.
The quantity is always computed by deterministic Python (the LLM never does the
math); when Gemini is configured it may enrich the rationale using a Pydantic
response schema.  The rules engine (Stage 2) has final say regardless.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from backend.config import settings
from models.allocation_models import AccountSnapshot, TradeProposal

# Default target allocation % used by the deterministic proposer.  Set above the
# conservative cap so the rules-engine override is visibly demonstrated.
DEFAULT_TARGET_PCT = 0.30


def _pick_symbol(snapshot: AccountSnapshot, market_facts: Dict[str, Any],
                 requested: Optional[str]) -> str:
    if requested:
        return requested
    if market_facts.get("symbol"):
        return market_facts["symbol"]
    if snapshot.holdings:
        # Prefer the largest existing holding.
        return max(snapshot.holdings, key=lambda h: h.market_value).symbol
    return "RELIANCE"


def propose_allocation(snapshot: AccountSnapshot, market_facts: Dict[str, Any],
                       symbol: Optional[str] = None, target_pct: Optional[float] = None,
                       confidence: Optional[str] = None) -> TradeProposal:
    """Deterministic proposal. ``target_pct`` defaults to a deliberately large
    value so the rules engine visibly resizes it during the demo."""
    symbol = _pick_symbol(snapshot, market_facts, symbol)
    price = float(market_facts.get("price") or 100.0)
    pct = float(target_pct if target_pct is not None else DEFAULT_TARGET_PCT)
    desired_value = snapshot.portfolio_value * pct
    quantity = math.floor(desired_value / price) if price > 0 else 0
    qty = max(0, quantity)

    trend = market_facts.get("trend") or "NEUTRAL"
    if confidence is None:
        confidence = "HIGH" if trend == "UPTREND" else ("MEDIUM" if trend == "NEUTRAL" else "LOW")

    rationale = (
        f"{symbol} trades at {price:,.2f} (trend {trend}); proposing a "
        f"{pct * 100:.0f}% allocation of the {snapshot.risk_profile} portfolio."
    )

    proposal = TradeProposal(symbol=symbol, side="BUY", proposed_quantity=float(qty),
                             rationale=rationale, confidence=confidence, proposer="ai_gemini" if _gemini() else "ai_deterministic")
    if _gemini():
        enriched = _gemini_rationale(symbol, price, trend, snapshot.risk_profile, pct)
        if enriched:
            proposal.rationale = enriched
    return proposal


def _gemini() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _gemini_rationale(symbol: str, price: float, trend: str, profile: str, pct: float) -> Optional[str]:
    """Optional rationale enrichment (never computes a number)."""
    try:
        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=(f"Write a one-sentence advisory rationale (no numbers beyond the given values) "
                      f"for choosing a {pct * 100:.0f}% allocation in {symbol} (price {price:,.2f}, trend {trend}) "
                      f"for a {profile} investor. It is paper trading."),
            config={"temperature": 0, "max_output_tokens": 120,
                    "system_instruction": "You never compute financial values; you only phrase the rationale."},
        )
        return resp.text.strip() if resp.text else None
    except Exception:
        return None

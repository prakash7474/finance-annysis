"""
narrator.py - FinPilot's financial narrator.

The narrator ONLY explains validated facts produced by the deterministic
engines.  It is explicitly instructed never to compute, invent or modify
financial values.  When Gemini is unavailable a deterministic fallback turns the
same facts into a concise plain-language summary, so the app always responds.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.config import settings


NARRATOR_SYSTEM_PROMPT = """You are FinPilot's financial narrator.

You MUST only use validated facts supplied by deterministic backend tools.

Never calculate financial values yourself.
Never invent balances, rates, EMIs, risks, prices or market indicators.
Never modify a numerical value.
If a value is missing, say that it is unavailable.
Clearly distinguish factual calculations from general guidance.
Do not claim guaranteed financial outcomes.
Use concise, understandable language.
Format money in Indian Rupees (₹).
Risk levels: HEALTHY, LOW, MODERATE, HIGH, CRITICAL.
"""


def _money(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"₹{value:,.2f}"


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%" if value <= 1.5 else f"{value:.1f}%"


def fallback_narration(facts: Dict[str, Any], intent: Optional[str] = None) -> str:
    """Deterministic plain-language summary of the facts."""
    parts: list[str] = []
    domain = facts.get("domain") or intent

    cash = facts.get("cash_position") or facts.get("cash")
    if cash:
        net = cash.get("net_cash")
        parts.append(f"Your current net cash is {_money(net)}.")
        accounts = cash.get("accounts")
        if accounts:
            for acc in accounts[:3]:
                parts.append(f"  {acc.get('account_name', acc.get('account_id'))}: {_money(acc.get('balance'))}")

    baseline = facts.get("baseline")
    if baseline:
        if baseline.get("monthly_income") is not None:
            parts.append(f"Your monthly income is {_money(baseline['monthly_income'])}.")
        if baseline.get("existing_emi") is not None:
            parts.append(f"Your existing recurring EMI burden is {_money(baseline['existing_emi'])}.")

    loan = facts.get("loan")
    if loan:
        if loan.get("amount") is not None:
            parts.append(f"For a loan of {_money(loan.get('amount'))} at {loan.get('rate')}% over {loan.get('tenure_months')} months:")
        if loan.get("emi") is not None:
            parts.append(f"  Monthly EMI: {_money(loan['emi'])}.")
        if loan.get("total_interest") is not None:
            parts.append(f"  Total interest: {_money(loan['total_interest'])}.")
        if loan.get("dti") is not None:
            parts.append(f"  This brings your debt-to-income ratio to {_pct(loan['dti'])}.")
        if loan.get("risk_level") is not None:
            parts.append(f"  Risk level: {loan['risk_level']}.")

    health = facts.get("health")
    if health:
        parts.append(f"Your financial health score is {health.get('overall_score')}/100 ({health.get('risk_level')}).")
        for warning in health.get("warnings", [])[:3]:
            parts.append(f"  Note: {warning}")

    market = facts.get("market")
    if market:
        if market.get("symbol") and market.get("price") is not None:
            parts.append(f"{market['symbol']} is trading at {_money(market['price'])}.")
        if market.get("trend"):
            parts.append(f"Trend vs {market.get('sma_days', 20)}-day SMA: {market['trend']} ({market.get('pct_diff')}%).")
        if market.get("momentum_pct") is not None:
            parts.append(f"10-day momentum: {market['momentum_pct']:+.2f}%.")

    offers = facts.get("offers")
    if offers:
        parts.append("Loan comparison (by total cost):")
        for offer in offers[:4]:
            parts.append(f"  {offer.get('bank')} @ {offer.get('interest_rate')}% / {offer.get('tenure_months')}m -> EMI {_money(offer.get('emi'))}, total {_money(offer.get('total_cost'))}, risk {offer.get('risk_level')}.")

    scenario = facts.get("scenario")
    if scenario:
        cur, scn = scenario.get("current", {}), scenario.get("scenario", {})
        parts.append("What-if comparison:")
        parts.append(f"  Current income {_money(cur.get('monthly_income'))} -> scenario {_money(scn.get('monthly_income'))}.")
        parts.append(f"  Current EMI {_money(cur.get('emi'))} -> scenario {_money(scn.get('emi'))}.")
        parts.append(f"  Current DTI {_pct(cur.get('dti_ratio'))} -> scenario {_pct(scn.get('dti_ratio'))}.")
        parts.append(f"  Current risk {cur.get('risk')} -> scenario {scn.get('risk')}.")

    if not parts:
        return "I couldn't find a matching capability for that request."

    return "\n".join(parts)


class Narrator:
    """Gemini narrator with deterministic fallback."""

    def __init__(self, client=None, model: Optional[str] = None):
        self.client = client
        self.model = model or settings.GEMINI_MODEL

    @property
    def available(self) -> bool:
        return bool(self.client) and bool(settings.GEMINI_API_KEY)

    def narrate(self, facts: Dict[str, Any], intent: Optional[str] = None,
                user_message: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[str, str]:
        """Return (text, source). source is 'gemini' or 'fallback'."""
        if self.available:
            try:
                text = self._gemini(facts, intent, user_message)
                if text:
                    return text, "gemini"
            except Exception:
                pass
        return fallback_narration(facts, intent), "fallback"

    def _gemini(self, facts: Dict[str, Any], intent: Optional[str], user_message: Optional[str]) -> str:
        prompt = (
            f"User asked: {user_message or '(no message)'}\n"
            f"Validated deterministic facts (JSON): {facts}\n\n"
            "Explain these facts in plain, concise language (under 200 words). "
            "Do not recompute any number. Do not add hypothetical figures."
        )
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"system_instruction": NARRATOR_SYSTEM_PROMPT, "temperature": 0.3,
                    "max_output_tokens": 400},
        )
        return resp.text


def make_narrator() -> "Narrator":
    """Build a Narrator, wiring a Gemini client only when a key is configured."""
    if not settings.GEMINI_API_KEY:
        return Narrator(client=None)
    try:
        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return Narrator(client=client)
    except Exception:
        return Narrator(client=None)

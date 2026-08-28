"""
router.py - Intent routing.

A deterministic routing layer decides which backend capabilities a request
needs.  Keyword routing is the primary path (fast, reliable and deterministic);
when a query is ambiguous, Gemini may be asked for a *structured* intent that is
validated with Pydantic before use.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.orchestrator.context import SessionContext
from backend.schemas.chat import IntentResult

DOMAIN_FINANCE = "FINANCE"
DOMAIN_LOAN = "LOAN"
DOMAIN_MARKET = "MARKET"
DOMAIN_GENERAL = "GENERAL"
DOMAIN_MULTI = "MULTI_DOMAIN"

# Known NSE symbols (seed the mock adapter).
KNOWN_SYMBOLS = {
    "RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK", "SBIN", "WIPRO", "ITC",
    "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "MARUTI",
    "SUNPHARMA", "ADANIENT", "TATAMOTORS", "NIFTY50", "SENSEX",
    "hdfc", "icici", "axis", "sbi",
}

FINANCE_KEYWORDS = ["cash", "balance", "position", "account", "spend", "spent", "income", "credit",
                    "debit", "emi", "summary", "salary", "transaction", "category", "health",
                    "afford", "runway", "financial"]
LOAN_KEYWORDS = ["loan", "borrow", "emi", "tenure", "interest", "lakh", "lac", "percent", "%",
                 "repay", "repayment", "compare", "what if", "what-if", "afford", "scenario"]
MARKET_KEYWORDS = ["stock", "price", "share", "market", "trend", "momentum", "ohlc", "sma",
                   "performing", "quote", "up", "down", "invest"]


# ──────────────────────────────────────────────────────────────────────────────
# Entity parsing (deterministic)
# ──────────────────────────────────────────────────────────────────────────────

def _parse_amount(text: str) -> Optional[float]:
    # Normalize: drop the rupee symbol and Indian lakh-style commas.
    cleaned = re.sub(r"[\u20b9\s]", "", text)
    cleaned = re.sub(r",", "", cleaned)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lac|lakhs|lacs|crore|crores|cr)?", cleaned, re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1))
    unit = (m.group(2) or "").lower() if m.group(2) else ""
    if unit.startswith("cr"):
        value *= 10_000_000
    elif unit.startswith("lakh") or unit.startswith("lac"):
        value *= 100_000
    else:
        # A bare number must be a plausible loan amount (~₹1,000+) to be treated
        # as an amount, otherwise it could be a tenure or rate ("36 months").
        if value < 1000:
            return None
    return value


def _parse_rate(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if m:
        return float(m.group(1))
    # "at 12" pattern: "loan at 12 for 36"
    m = re.search(r"\bat\s+(\d+(?:\.\d+)?)\b", text)
    if m:
        return float(m.group(1))
    return None


def _parse_tenure(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(months|month|years|year)", text, re.IGNORECASE)
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("year"):
        return value * 12
    return value


def _parse_symbol(text: str) -> Optional[str]:
    upper = text.upper()
    for sym in sorted(KNOWN_SYMBOLS, key=len, reverse=True):
        if f" {sym} " in f" {upper} " or upper.startswith(f"{sym} ") or upper.endswith(f" {sym}"):
            return sym
    return None


def _parse_salary_change(text: str) -> Optional[float]:
    m = re.search(r"(?:falls|drop?s?|decrease|reduc|decreas|down)\s*by\s*(-?\d+(?:\.\d+)?)\s*%", text, re.IGNORECASE)
    if m:
        return -float(m.group(1))
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*%\s*(?:salary|income)", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def parse_entities(message: str) -> Dict[str, Any]:
    entities: Dict[str, Any] = {}
    amount = _parse_amount(message)
    if amount:
        entities["loan_amount"] = amount
        entities["amount"] = amount
    rate = _parse_rate(message)
    if rate:
        entities["rate"] = rate
    tenure = _parse_tenure(message)
    if tenure:
        entities["tenure_months"] = tenure
    symbol = _parse_symbol(message)
    if symbol:
        entities["symbol"] = symbol
    sal = _parse_salary_change(message)
    if sal is not None:
        entities["salary_change_percent"] = sal
    return entities


# ──────────────────────────────────────────────────────────────────────────────
# Deterministic intent detection
# ──────────────────────────────────────────────────────────────────────────────

def _has_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


def detect_intent(message: str, context: Optional[SessionContext] = None) -> Tuple[IntentResult, Dict[str, Any]]:
    text = message.lower()
    entities = parse_entities(message)

    finance_tools: List[str] = []
    loan_tools: List[str] = []
    market_tools: List[str] = []

    # Finance
    if _has_any(text, ["health", "financial health"]):
        finance_tools.append("calculate_health_score")
    if _has_any(text, ["cash", "balance", "position", "available cash", "how much cash"]):
        finance_tools.append("get_cash_position")
    if _has_any(text, ["emi summary", "emi breakdown", "list my emi", "my emis"]):
        finance_tools.append("get_emi_summary")
    if _has_any(text, ["category", "spending by", "categories"]):
        finance_tools.append("get_category_summary")
    if _has_any(text, ["income", "credit", "debit", "summary", "spend", "this month", "cash flow"]):
        finance_tools.append("get_monthly_summary")
    if _has_any(text, ["afford", "current cash", "my cash", "income and", "financial position"]):
        finance_tools.append("get_financial_baseline")

    # Loan
    if _has_any(text, ["compare", "hdfc", "icici", "axis", "sbi", "bank offer"]):
        loan_tools.append("compare_loan_offers")
    if _has_any(text, ["what if", "what-if", "scenario", "extend tenure", "reduce", "salary falls", "salary drop", "salary decrease"]):
        loan_tools.append("run_scenario")
    if _has_any(text, ["loan", "borrow", "emi for", "repay", "lakh", "lac", "tenure", "interest rate"]):
        if "scenario" not in text and not _has_any(text, ["what if", "what-if"]):
            loan_tools.append("calculate_loan")
        if not loan_tools:
            loan_tools.append("calculate_loan")

    # Market
    if entities.get("symbol") or _has_any(text, ["stock", "market", "trend", "momentum", "price of", "share", "performing"]):
        if entities.get("symbol"):
            market_tools.append("get_quote")
            market_tools.append("get_trend")
            if _has_any(text, ["momentum"]):
                market_tools.append("get_momentum")
            if _has_any(text, ["ohlc", "history", "range"]):
                market_tools.append("get_ohlc")
        else:
            market_tools.append("get_quote")

    # De-dup and order
    finance_tools = _dedupe(finance_tools)
    loan_tools = _dedupe(loan_tools)
    market_tools = _dedupe(market_tools)

    has_finance = bool(finance_tools)
    has_loan = bool(loan_tools)
    has_market = bool(market_tools)

    if has_finance and has_loan:
        intent = DOMAIN_MULTI
        required = finance_tools + loan_tools
        # Multi-domain affordability always needs DTI + health for a holistic view.
        if "calculate_dti" not in required:
            required.append("calculate_dti")
        if "calculate_health_score" not in required:
            required.append("calculate_health_score")
        confidence = 0.88
    elif has_finance and has_market:
        intent = DOMAIN_MULTI
        required = finance_tools + market_tools
        confidence = 0.8
    elif has_finance:
        intent = DOMAIN_FINANCE
        required = finance_tools
        confidence = 0.9
    elif has_loan:
        intent = DOMAIN_LOAN
        required = loan_tools
        confidence = 0.9
    elif has_market:
        intent = DOMAIN_MARKET
        required = market_tools
        confidence = 0.85
    else:
        intent = DOMAIN_GENERAL
        required = []
        confidence = 0.4

    # Ordering: financial baseline / income first for multi-domain affordability.
    if intent == DOMAIN_MULTI and "get_financial_baseline" in required:
        required.sort(key=lambda t: 0 if t in ("get_financial_baseline", "get_cash_position") else 1)

    return IntentResult(intent=intent, required_tools=required, confidence=confidence), entities


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Optional Gemini structured intent (validated with Pydantic)
# ──────────────────────────────────────────────────────────────────────────────

def gemini_intent(client, message: str, model: str) -> Optional[IntentResult]:
    """Ask Gemini for a structured intent; validate with Pydantic. Returns None on failure."""
    prompt = (
        "Classify the user's request into one of FINANCE, LOAN, MARKET, GENERAL or MULTI_DOMAIN "
        "and list the backend tools needed. Tools available: "
        "get_cash_position, get_monthly_summary, get_emi_summary, get_category_summary, "
        "get_financial_baseline, calculate_health_score, calculate_loan, calculate_emi, "
        "calculate_dti, get_loan_offers, compare_loan_offers, what_if_tenure, run_scenario, "
        "get_quote, get_ohlc, get_trend, get_momentum.\n"
        "Respond with ONLY a JSON object exactly like:\n"
        '{"intent": "MULTI_DOMAIN", "required_tools": ["get_cash_position", "calculate_dti", "calculate_loan"], '
        '"confidence": 0.9}\n'
        f"USER REQUEST: {message}"
    )
    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json", "max_output_tokens": 256},
        )
        text = resp.text.strip()
        return IntentResult.model_validate_json(text)
    except Exception:
        return None

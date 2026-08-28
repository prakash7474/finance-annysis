"""
finance_chat.py - Unified AI Finance Chat (Phase 4)

Single chat interface that combines:
  - Phase 1: Cash position & transactions (finance_engine + bank MCP data)
  - Phase 2: EMI & loan analysis (loan_engine + loan offers)
  - Phase 3: Stock prices & trends (market_engine + mock market data)

Uses Google Gemini with automatic function calling (AFC) to:
  1. Detect user intent (finance / loan / market / general)
  2. Call the right engine functions behind the scenes
  3. Return structured answers with numbers, risk notes, and tables

Usage:
    python finance_chat.py
"""

import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

import finance_engine as fe
import loan_engine as le
import market_engine as me
from mock_market_adapter import MockMarketAdapter

# Fix Windows console encoding for ₹ and other Unicode characters
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ──────────────────────────────────────────────────────────────────────────────
# Gemini client setup
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not set. Add it to .env file.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# ──────────────────────────────────────────────────────────────────────────────
# Load mock data once
# ──────────────────────────────────────────────────────────────────────────────

DATA_FILE = Path(__file__).parent / "mock_data.json"
_mock_data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

# Market adapter (deterministic mock)
_market_adapter = MockMarketAdapter(seed=42)


# ──────────────────────────────────────────────────────────────────────────────
# Tool functions — Finance (Phase 1)
# ──────────────────────────────────────────────────────────────────────────────


def get_cash_position() -> dict:
    """Get current cash position across all bank accounts.

    Returns per-account balances and net cash.
    Use this when the user asks about their cash, balance, or account status.
    """
    return fe.compute_cash_position(_mock_data["accounts"], _mock_data["transactions"])


def get_monthly_summary(start_date: str, end_date: str) -> dict:
    """Summarize total credit, total debit, and net change in a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format (e.g., 2026-08-01).
        end_date: End date in YYYY-MM-DD format (e.g., 2026-08-31).

    Use this when the user asks about spending, income, or cash flow for a period.
    """
    return fe.summarize_credit_debit(
        _mock_data["transactions"], start_date, end_date
    )


def get_emi_summary(start_date: str, end_date: str) -> dict:
    """Get EMI summary for a date range. Shows all EMIs paid in that period.

    Args:
        start_date: Start date in YYYY-MM-DD format (e.g., 2026-08-01).
        end_date: End date in YYYY-MM-DD format (e.g., 2026-08-31).

    Use this when the user asks about EMIs, loan payments, or EMI breakdown.
    """
    return fe.detect_emis(_mock_data["transactions"], start_date, end_date)


def get_category_summary(start_date: str, end_date: str) -> dict:
    """Summarize spending by category within a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Use this when the user asks about spending breakdown or categories.
    """
    return fe.get_category_summary(_mock_data["transactions"], start_date, end_date)


# ──────────────────────────────────────────────────────────────────────────────
# Tool functions — Loan (Phase 2)
# ──────────────────────────────────────────────────────────────────────────────


def analyze_loan(
    amount: float,
    rate: float,
    tenure_months: int,
    monthly_income: float,
    existing_emi: float = 0,
) -> dict:
    """Analyze a single loan scenario: compute EMI, total cost, and risk assessment.

    Args:
        amount: Loan amount in INR (e.g., 300000 for 3 lakh).
        rate: Annual interest rate in percent (e.g., 12.0).
        tenure_months: Loan tenure in months (e.g., 36).
        monthly_income: Monthly income in INR (e.g., 80000).
        existing_emi: Existing monthly EMI in INR (default 0).

    Returns:
        Dictionary with emi, total_interest, total_cost, risk_level, risk_flags.
    """
    return le.assess_loan_risk(
        principal=amount,
        annual_rate_pct=rate,
        tenure_months=tenure_months,
        monthly_income=monthly_income,
        existing_monthly_emi=existing_emi,
    )


def compare_loan_offers(
    amount: float,
    monthly_income: float,
    existing_emi: float = 0,
    bank_filter: str = "",
) -> list[dict]:
    """Compare available loan offers from banks and rank by total cost.

    Args:
        amount: Loan amount in INR.
        monthly_income: Monthly income in INR.
        existing_emi: Existing monthly EMI in INR (default 0).
        bank_filter: Optional comma-separated bank names to filter (e.g., "HDFC,ICICI").

    Returns:
        List of offers ranked by total cost with EMI, risk level, and flags.
    """
    offers = _mock_data["loan_offers"]

    if bank_filter:
        bank_list = [b.strip().upper() for b in bank_filter.split(",")]
        offers = [
            o for o in offers
            if any(bank in o["bank"].upper() for bank in bank_list)
        ]

    return le.compare_loan_offers(
        principal=amount,
        offers=offers,
        monthly_income=monthly_income,
        existing_monthly_emi=existing_emi,
    )


def what_if_tenure(
    amount: float,
    rate: float,
    current_tenure: int,
    proposed_tenure: int,
    monthly_income: float,
) -> dict:
    """Compare how EMI and total cost change if tenure is extended or shortened.

    Args:
        amount: Loan amount in INR.
        rate: Annual interest rate in percent.
        current_tenure: Current tenure in months.
        proposed_tenure: Proposed new tenure in months.
        monthly_income: Monthly income in INR.

    Returns:
        Dictionary with current vs proposed comparison and differences.
    """
    current = le.assess_loan_risk(amount, rate, current_tenure, monthly_income)
    proposed = le.assess_loan_risk(amount, rate, proposed_tenure, monthly_income)

    return {
        "current": {
            "tenure_months": current_tenure,
            "emi": current["emi"],
            "total_interest": current["total_interest"],
            "total_cost": current["total_cost"],
            "emi_income_ratio": current["emi_income_ratio"],
        },
        "proposed": {
            "tenure_months": proposed_tenure,
            "emi": proposed["emi"],
            "total_interest": proposed["total_interest"],
            "total_cost": proposed["total_cost"],
            "emi_income_ratio": proposed["emi_income_ratio"],
        },
        "difference": {
            "emi_change": round(proposed["emi"] - current["emi"], 2),
            "interest_change": round(
                proposed["total_interest"] - current["total_interest"], 2
            ),
            "cost_change": round(proposed["total_cost"] - current["total_cost"], 2),
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tool functions — Market (Phase 3)
# ──────────────────────────────────────────────────────────────────────────────


def get_stock_price(symbol: str) -> dict:
    """Get the latest stock price for a given symbol.

    Args:
        symbol: Stock symbol (e.g., "RELIANCE", "INFY", "TCS").

    Use this when the user asks about the current price of a stock.
    """
    price = _market_adapter.get_latest_price(symbol)
    return {"symbol": symbol.upper(), "price": price}


def get_stock_trend(symbol: str, sma_days: int = 20) -> dict:
    """Analyze the trend of a stock by comparing its latest close to the SMA.

    Args:
        symbol: Stock symbol (e.g., "INFY").
        sma_days: SMA window in days (default 20).

    Returns latest close, SMA value, trend (UPTREND/DOWNTREND/NEUTRAL), and % difference.

    Use this when the user asks about trend, direction, or whether a stock is going up/down.
    """
    days_needed = max(sma_days * 2, 60)
    bars = _market_adapter.get_ohlc_history(symbol, days_needed)
    return me.detect_trend_vs_sma(bars, sma_days=sma_days)


def get_stock_momentum(symbol: str, lookback_days: int = 10) -> dict:
    """Compute price momentum for a stock over the last N days.

    Args:
        symbol: Stock symbol (e.g., "TCS").
        lookback_days: Number of days to look back (default 10).

    Returns momentum percentage, older close, and latest close.

    Use this when the user asks about momentum, recent performance, or % change.
    """
    days_needed = lookback_days + 5
    bars = _market_adapter.get_ohlc_history(symbol, days_needed)
    return me.compute_momentum(bars, lookback_days=lookback_days)


def get_stock_ohlc(symbol: str, days: int = 30) -> dict:
    """Get OHLC (Open/High/Low/Close) history for a stock.

    Args:
        symbol: Stock symbol (e.g., "RELIANCE").
        days: Number of days of history (default 30).

    Use this when the user asks for price history or OHLC data.
    """
    bars = _market_adapter.get_ohlc_history(symbol, days)
    return {"symbol": symbol.upper(), "bars": bars, "count": len(bars)}


def get_stock_high_low(symbol: str, days: int = 20) -> dict:
    """Compute the high/low price range for a stock over the last N days.

    Args:
        symbol: Stock symbol (e.g., "INFY").
        days: Number of days (default 20).

    Use this when the user asks about price range, volatility, or support/resistance.
    """
    bars = _market_adapter.get_ohlc_history(symbol, days + 5)
    return me.compute_high_low_range(bars, days=days)


# ──────────────────────────────────────────────────────────────────────────────
# Tool functions — Combined / Cross-domain
# ──────────────────────────────────────────────────────────────────────────────


def loan_with_cash_context(
    amount: float,
    rate: float,
    tenure_months: int,
    monthly_income: float,
    existing_emi: float = 0,
) -> dict:
    """Analyze a loan while considering the user's current cash position and EMI burden.

    This combines loan analysis with the user's actual financial data to give
    a holistic view: can they afford this loan given their current EMIs and cash?

    Args:
        amount: Loan amount in INR.
        rate: Annual interest rate in percent.
        tenure_months: Loan tenure in months.
        monthly_income: Monthly income in INR.
        existing_emi: Existing monthly EMI in INR (default 0).

    Returns loan analysis plus current EMI data and cash position.
    """
    # Loan analysis
    loan_result = le.assess_loan_risk(
        principal=amount,
        annual_rate_pct=rate,
        tenure_months=tenure_months,
        monthly_income=monthly_income,
        existing_monthly_emi=existing_emi,
    )

    # Current EMI summary (current month)
    today = datetime.now()
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    month_end = today.strftime("%Y-%m-%d")
    emi_data = fe.detect_emis(_mock_data["transactions"], month_start, month_end)

    # Cash position
    cash = fe.compute_cash_position(_mock_data["accounts"], _mock_data["transactions"])

    return {
        "loan_analysis": loan_result,
        "current_emis": {
            "total_emi": emi_data["total_emi"],
            "emi_count": emi_data["emi_count"],
            "breakdown": emi_data["emi_breakdown"],
        },
        "cash_position": {
            "net_cash": cash["net_cash"],
            "accounts": cash["accounts"],
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI Finance Controller — a unified finance assistant for an Indian user.

You combine expertise across three domains:

1. PERSONAL FINANCE (cash, transactions, EMIs):
   - Cash position across bank accounts
   - Monthly spending/income summary
   - EMI tracking and breakdown
   - Category-wise spending analysis

2. LOAN ANALYSIS:
   - EMI calculation and total cost
   - Risk assessment based on income and existing EMIs
   - Comparing multiple loan offers
   - What-if analysis (changing tenure, rate, etc.)

3. MARKET DATA:
   - Latest stock prices
   - Trend analysis (vs SMA)
   - Price momentum
   - OHLC history and high/low ranges

RULES:
- Always use Indian Rupee formatting (₹ symbol, Indian number format like 3,00,000)
- Be concise and direct — give numbers first, then context
- When risk is MEDIUM or HIGH, always add a clear caution
- When comparing loans, highlight the best option by cost AND by risk
- If the user hasn't provided income or existing EMI for loan analysis, ask for them
- For what-if analysis, clearly show the trade-off (lower EMI vs higher total interest)
- When answering market questions, mention the trend direction and key levels
- Use the tools to compute accurate numbers — never guess EMI values or stock prices
- If a user's question spans multiple domains (e.g., "given my cash, can I afford this loan?"),
  use the loan_with_cash_context tool for a holistic answer
- For date ranges, default to the current month (2026-08-01 to 2026-08-27) unless specified
- Keep responses under 200 words unless the user asks for details
"""


# ──────────────────────────────────────────────────────────────────────────────
# Chat loop
# ──────────────────────────────────────────────────────────────────────────────


def run_chat():
    """Run interactive chat loop with Gemini AFC."""
    print("=" * 60)
    print("  AI Finance Controller  (Powered by Gemini)")
    print("  Unified: Finance + Loan + Market")
    print("  Type 'quit' or 'exit' to stop")
    print("=" * 60)
    print()
    print("Try asking about:")
    print("  Finance:")
    print("    - What's my cash position this month?")
    print("    - How much did I spend in August?")
    print("    - List my EMIs for July.")
    print("  Loan:")
    print("    - Is a ₹3L loan at 12% for 36 months okay for me?")
    print("    - Compare HDFC vs ICICI for ₹2L, income ₹80k.")
    print("    - What if I extend my tenure from 24 to 36 months?")
    print("  Market:")
    print("    - What's the current price of RELIANCE?")
    print("    - How is INFY trending?")
    print("    - Show momentum for TCS.")
    print("  Combined:")
    print("    - Given my cash and EMIs, is a ₹3L loan safe?")
    print()

    # Collect all tool functions
    all_tools = [
        get_cash_position,
        get_monthly_summary,
        get_emi_summary,
        get_category_summary,
        analyze_loan,
        compare_loan_offers,
        what_if_tenure,
        get_stock_price,
        get_stock_trend,
        get_stock_momentum,
        get_stock_ohlc,
        get_stock_high_low,
        loan_with_cash_context,
    ]

    # Create chat session with tools
    chat = client.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            tools=all_tools,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        ),
    )

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        try:
            resp = chat.send_message(user_input)
            print(f"\nAdvisor: {resp.text}\n")
        except Exception as e:
            print(f"\n[Error: {e}]\n")


# ──────────────────────────────────────────────────────────────────────────────
# Quick demo (non-interactive) for testing
# ──────────────────────────────────────────────────────────────────────────────


def demo():
    """Run a few scripted queries to demo the unified controller."""
    print("=" * 60)
    print("  AI Finance Controller — Demo Mode")
    print("=" * 60)

    all_tools = [
        get_cash_position,
        get_monthly_summary,
        get_emi_summary,
        get_category_summary,
        analyze_loan,
        compare_loan_offers,
        what_if_tenure,
        get_stock_price,
        get_stock_trend,
        get_stock_momentum,
        get_stock_ohlc,
        get_stock_high_low,
        loan_with_cash_context,
    ]

    chat = client.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            tools=all_tools,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        ),
    )

    demo_queries = [
        "What's my cash position this month?",
        "How is INFY trending?",
        "Analyze a ₹3L loan at 12% for 36 months. My income is ₹80,000 and existing EMI is ₹22,300.",
        "What if I take it for 24 months instead?",
    ]

    for q in demo_queries:
        print(f"\n{'-' * 60}")
        print(f"You: {q}")
        print(f"{'-' * 60}")
        try:
            resp = chat.send_message(q)
            print(f"Advisor: {resp.text}")
        except Exception as e:
            print(f"[Error: {e}]")

    print(f"\n{'=' * 60}")
    print("  Demo complete.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        run_chat()

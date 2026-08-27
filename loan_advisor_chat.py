"""
loan_advisor_chat.py - AI Loan Advisor Chatbot (Gemini-powered)

Uses Google Gemini API with automatic function calling (AFC) to answer
loan questions. Integrates with loan_engine.py and finance_engine.py.

Usage:
    python loan_advisor_chat.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

import loan_engine as le
import finance_engine as fe

# ──────────────────────────────────────────────────────────────────────────────
# Gemini client setup
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# ──────────────────────────────────────────────────────────────────────────────
# Tool functions (Gemini auto-discovers these via docstrings + type hints)
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
) -> list[dict]:
    """Compare available loan offers from banks and rank by total cost.

    Args:
        amount: Loan amount in INR.
        monthly_income: Monthly income in INR.
        existing_emi: Existing monthly EMI in INR (default 0).

    Returns:
        List of offers ranked by total cost with EMI, risk level, and flags.
    """
    data_file = Path(__file__).parent / "mock_data.json"
    data = json.loads(data_file.read_text(encoding="utf-8"))
    offers = data["loan_offers"]

    return le.compare_loan_offers(
        principal=amount,
        offers=offers,
        monthly_income=monthly_income,
        existing_monthly_emi=existing_emi,
    )


def get_cash_position() -> dict:
    """Get current cash position across all bank accounts.

    Returns:
        Dictionary with per-account balances and net cash.
    """
    data_file = Path(__file__).parent / "mock_data.json"
    data = json.loads(data_file.read_text(encoding="utf-8"))
    return fe.compute_cash_position(data["accounts"], data["transactions"])


def get_emi_summary(start_date: str, end_date: str) -> dict:
    """Get EMI summary for a date range. Shows all EMIs paid in that period.

    Args:
        start_date: Start date in YYYY-MM-DD format (e.g., 2026-08-01).
        end_date: End date in YYYY-MM-DD format (e.g., 2026-08-31).

    Returns:
        Dictionary with EMI list, total, and breakdown by lender.
    """
    data_file = Path(__file__).parent / "mock_data.json"
    data = json.loads(data_file.read_text(encoding="utf-8"))
    return fe.detect_emis(data["transactions"], start_date, end_date)


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
# System prompt
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI Finance Advisor chatbot for an Indian user.

You help with:
- Loan analysis: compute EMI, total cost, risk assessment
- Loan comparison: compare offers from different banks
- What-if analysis: show how changing tenure affects EMI and cost
- Personal finance: cash position, EMI tracking

Guidelines:
- Always use Indian Rupee formatting (Rs. or use commas like 3,00,000)
- Be concise and clear in responses
- Explain risk flags in simple terms
- Give actionable suggestions (e.g., "Consider extending tenure to reduce EMI")
- When comparing, highlight the best option by cost and by risk
- If the user hasn't provided income, ask for it before running analysis
- For what-if analysis, clearly show the trade-off (lower EMI vs higher total interest)
- Use the tools to compute accurate numbers, never guess EMI values
"""


# ──────────────────────────────────────────────────────────────────────────────
# Chat loop
# ──────────────────────────────────────────────────────────────────────────────


def run_chat():
    """Run interactive chat loop with Gemini AFC."""
    print("=" * 60)
    print("  AI Loan Advisor  (Powered by Gemini)")
    print("  Type 'quit' or 'exit' to stop")
    print("=" * 60)
    print()
    print("Examples:")
    print("  - I want to take a 3 lakh loan at 12% for 36 months.")
    print("  - Compare HDFC vs ICICI for 2 lakh loan, income 80k.")
    print("  - What if I extend my tenure from 24 to 36 months?")
    print("  - What's my current cash position?")
    print("  - Show my EMIs for August 2026.")
    print()

    # Create chat session with tools
    chat = client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            tools=[analyze_loan, compare_loan_offers, get_cash_position, get_emi_summary, what_if_tenure],
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


if __name__ == "__main__":
    run_chat()

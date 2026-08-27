"""
finance_engine.py - Pure Python finance analysis functions.

No MCP logic here; just data transformations on accounts and transactions.
"""

from datetime import date, datetime
from typing import Iterable


def compute_cash_position(accounts: list[dict], transactions: Iterable[dict]) -> dict:
    """
    Compute current cash position per account and overall.
    
    cash = opening_balance + sum(credits) - sum(debits)
    """
    opening = {a["account_id"]: a["opening_balance"] for a in accounts}
    balance = dict(opening)

    for t in transactions:
        acc = t["account_id"]
        amt = t["amount"]
        if t["type"] == "CREDIT":
            balance[acc] = balance.get(acc, 0) + amt
        else:
            balance[acc] = balance.get(acc, 0) - amt

    # Build account name lookup
    name_map = {a["account_id"]: a["account_name"] for a in accounts}
    type_map = {a["account_id"]: a["account_type"] for a in accounts}

    result = {
        "accounts": [],
        "net_cash": 0.0,
    }
    for acc_id, bal in balance.items():
        result["accounts"].append({
            "account_id": acc_id,
            "account_name": name_map.get(acc_id, acc_id),
            "account_type": type_map.get(acc_id, "UNKNOWN"),
            "balance": round(bal, 2),
        })
        result["net_cash"] += bal
    result["net_cash"] = round(result["net_cash"], 2)

    return result


def summarize_credit_debit(
    transactions: Iterable[dict],
    start_date: str,
    end_date: str,
) -> dict:
    """
    Summarize total credit, total debit, and net change within a date range.
    """
    total_credit = 0.0
    total_debit = 0.0
    txn_count = 0

    for t in transactions:
        if not (start_date <= t["date"] <= end_date):
            continue
        txn_count += 1
        if t["type"] == "CREDIT":
            total_credit += t["amount"]
        else:
            total_debit += t["amount"]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_credit": round(total_credit, 2),
        "total_debit": round(total_debit, 2),
        "net_change": round(total_credit - total_debit, 2),
        "transaction_count": txn_count,
    }


def detect_emis(
    transactions: Iterable[dict],
    start_date: str,
    end_date: str,
) -> dict:
    """
    Detect EMI transactions within a date range.
    
    Matches by category == "LOAN_EMI" or by pattern-matching descriptions.
    """
    known_lenders = [
        "HDFC PERSONAL LOAN",
        "ICICI PERSONAL LOAN",
        "SBI HOUSING LOAN",
        "AXIS CAR LOAN",
        "BAJAJ FINSERV",
        "TATA CAPITAL",
    ]

    emis = []
    total_emi = 0.0

    for t in transactions:
        if not (start_date <= t["date"] <= end_date):
            continue

        is_emi = False

        # Primary: category match
        if t.get("category") == "LOAN_EMI":
            is_emi = True

        # Fallback: pattern match on description
        if not is_emi:
            desc = t.get("description", "").upper()
            if "EMI" in desc or "LOAN" in desc:
                is_emi = True

        if is_emi:
            emis.append(t)
            total_emi += t["amount"]

    # Group by lender/product
    emi_breakdown = {}
    for t in emis:
        desc = t["description"]
        # Extract lender name from description like "EMI - HDFC PERSONAL LOAN"
        parts = desc.split(" - ", 1)
        lender = parts[1].strip() if len(parts) > 1 else desc
        emi_breakdown[lender] = emi_breakdown.get(lender, 0) + t["amount"]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "emis": emis,
        "total_emi": round(total_emi, 2),
        "emi_count": len(emis),
        "emi_breakdown": emi_breakdown,
    }


def compute_emi_income_ratio(
    transactions: Iterable[dict],
    start_date: str,
    end_date: str,
) -> dict:
    """
    Compute EMI-to-income ratio.
    """
    total_emi = 0.0
    total_income = 0.0

    for t in transactions:
        if not (start_date <= t["date"] <= end_date):
            continue

        # Sum income (salary + freelance + interest + dividend)
        if t["type"] == "CREDIT" and t.get("category") in (
            "SALARY", "FREELANCE", "INTEREST", "DIVIDEND"
        ):
            total_income += t["amount"]

        # Sum EMIs
        if t.get("category") == "LOAN_EMI" or "EMI" in t.get("description", "").upper():
            total_emi += t["amount"]

    ratio = (total_emi / total_income * 100) if total_income > 0 else 0.0

    return {
        "total_emi": round(total_emi, 2),
        "total_income": round(total_income, 2),
        "emi_income_ratio_pct": round(ratio, 2),
        "is_stressed": ratio > 40,
    }


def get_category_summary(
    transactions: Iterable[dict],
    start_date: str,
    end_date: str,
) -> dict:
    """
    Summarize spending by category within a date range.
    """
    categories = {}

    for t in transactions:
        if not (start_date <= t["date"] <= end_date):
            continue
        cat = t.get("category", "UNCATEGORIZED")
        if cat not in categories:
            categories[cat] = {"total": 0.0, "count": 0}
        categories[cat]["total"] += t["amount"]
        categories[cat]["count"] += 1

    # Round totals
    for cat in categories:
        categories[cat]["total"] = round(categories[cat]["total"], 2)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "categories": categories,
    }


def format_inr(amount: float) -> str:
    """Format amount in Indian Rupee style."""
    if amount < 0:
        return f"-₹{abs(amount):,.2f}"
    return f"₹{amount:,.2f}"


def format_cash_position(pos: dict) -> str:
    """Pretty-print cash position."""
    lines = ["Cash Position:"]
    lines.append("-" * 40)
    for acc in pos["accounts"]:
        lines.append(
            f"  {acc['account_name']} ({acc['account_id']}): "
            f"{format_inr(acc['balance'])}"
        )
    lines.append("-" * 40)
    lines.append(f"  Net cash: {format_inr(pos['net_cash'])}")
    return "\n".join(lines)


def format_monthly_summary(summary: dict) -> str:
    """Pretty-print monthly credit/debit summary."""
    lines = [
        f"Summary ({summary['start_date']} to {summary['end_date']}):",
        "-" * 40,
        f"  Total credit:  {format_inr(summary['total_credit'])}",
        f"  Total debit:   {format_inr(summary['total_debit'])}",
        f"  Net change:    {format_inr(summary['net_change'])}",
        f"  Transactions:  {summary['transaction_count']}",
    ]
    return "\n".join(lines)


def format_emi_summary(emi_data: dict) -> str:
    """Pretty-print EMI summary."""
    lines = [
        f"EMI Summary ({emi_data['start_date']} to {emi_data['end_date']}):",
        "-" * 40,
    ]

    for t in emi_data["emis"]:
        lines.append(f"  {t['date']} | {t['description']} | {format_inr(t['amount'])}")

    lines.append("-" * 40)
    lines.append(f"  Total EMI: {format_inr(emi_data['total_emi'])}")

    if emi_data["emi_breakdown"]:
        lines.append("\n  Breakdown by lender:")
        for lender, amt in emi_data["emi_breakdown"].items():
            lines.append(f"    {lender}: {format_inr(amt)}")

    return "\n".join(lines)

"""
anomaly_detector.py - Deterministic risk detection rules.

Pure functions that inspect accounts/transactions and return risk signals.
Thresholds are configurable.  No LLM is used.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def cash_position(accounts: List[Dict], transactions: List[Dict]) -> Dict[str, Any]:
    """Compute per-account balances and net cash (reuses finance_engine)."""
    import finance_engine as fe

    return fe.compute_cash_position(accounts, transactions)


def detect_large_debit(transactions: List[Dict], threshold: float) -> List[Dict[str, Any]]:
    signals = []
    for t in transactions:
        if t["type"] == "DEBIT" and t["amount"] >= threshold:
            signals.append({
                "category": "LARGE_DEBIT",
                "severity": "HIGH" if t["amount"] >= threshold * 2 else "MEDIUM",
                "account_id": t["account_id"],
                "message": f"Large debit of {t['amount']:,.2f} detected.",
                "amount": t["amount"],
                "txn_id": t.get("txn_id"),
            })
    return signals


def detect_large_credit(transactions: List[Dict], threshold: float) -> List[Dict[str, Any]]:
    signals = []
    for t in transactions:
        if t["type"] == "CREDIT" and t["amount"] >= threshold:
            signals.append({
                "category": "LARGE_CREDIT",
                "severity": "INFO",
                "account_id": t["account_id"],
                "message": f"Large credit of {t['amount']:,.2f} detected.",
                "amount": t["amount"],
                "txn_id": t.get("txn_id"),
            })
    return signals


def detect_liquidity_drop(accounts: List[Dict], transactions: List[Dict], min_balance: float) -> List[Dict[str, Any]]:
    position = cash_position(accounts, transactions)
    signals = []
    for account in position["accounts"]:
        if account["account_type"] == "CREDIT_CARD":
            continue
        if account["balance"] < min_balance:
            signals.append({
                "category": "LIQUIDITY",
                "severity": "HIGH",
                "account_id": account["account_id"],
                "account_name": account["account_name"],
                "message": f"Liquidity threshold breached: balance {account['balance']:,.2f} below {min_balance:,.2f}.",
                "balance": account["balance"],
            })
    return signals


def detect_high_emi_burden(transactions: List[Dict], monthly_income: float, ratio_threshold: float) -> List[Dict[str, Any]]:
    total_emi = sum(t["amount"] for t in transactions
                    if t["type"] == "DEBIT" and (t.get("category") == "LOAN_EMI" or "EMI" in t.get("description", "").upper()))
    if monthly_income <= 0:
        ratio = 0.0
    else:
        ratio = total_emi / monthly_income
    if ratio > ratio_threshold:
        return [{
            "category": "EMI_BURDEN",
            "severity": "HIGH" if ratio > 0.5 else "MEDIUM",
            "message": f"EMI burden is {ratio * 100:.1f}% of monthly income.",
            "total_emi": round(total_emi, 2),
            "ratio": round(ratio, 4),
        }]
    return []


def detect_unusual_spending(transactions: List[Dict], avg_daily: float, threshold_ratio: float) -> List[Dict[str, Any]]:
    """Flag a single debit that is much larger than the typical daily spend."""
    signals = []
    if avg_daily <= 0:
        return signals
    for t in transactions:
        if t["type"] == "DEBIT" and t["amount"] > avg_daily * threshold_ratio:
            signals.append({
                "category": "UNUSUAL_SPENDING",
                "severity": "MEDIUM" if t["amount"] > avg_daily * threshold_ratio * 2 else "LOW",
                "account_id": t["account_id"],
                "message": f"Unusual spending of {t['amount']:,.2f} vs typical {avg_daily:,.2f}/day.",
                "amount": t["amount"],
            })
    return signals


def detect_credit_utilization(accounts: List[Dict], utilization_threshold: float) -> List[Dict[str, Any]]:
    """Flag credit cards whose balance is large relative to a nominal limit."""
    signals = []
    nominal_limit = 200000.0
    for account in accounts:
        if account["account_type"] != "CREDIT_CARD":
            continue
        balance = account.get("opening_balance", 0.0)
        if abs(balance) >= nominal_limit * utilization_threshold:
            signals.append({
                "category": "CREDIT_UTILIZATION",
                "severity": "MEDIUM",
                "account_id": account["account_id"],
                "message": "High credit card utilization.",
                "balance": balance,
            })
    return signals


def detect_all(accounts: List[Dict], transactions: List[Dict], thresholds: Dict[str, float], monthly_income: float = 0.0) -> List[Dict[str, Any]]:
    """Run all detection rules and merge results."""
    signals: List[Dict[str, Any]] = []
    signals += detect_large_debit(transactions, thresholds["large_debit"])
    signals += detect_large_credit(transactions, thresholds["large_credit"])
    signals += detect_liquidity_drop(accounts, transactions, thresholds["liquidity_min_balance"])
    if monthly_income > 0:
        signals += detect_high_emi_burden(transactions, monthly_income, thresholds["emi_burden_ratio"])
    signals += detect_credit_utilization(accounts, thresholds["credit_utilization"])
    return signals

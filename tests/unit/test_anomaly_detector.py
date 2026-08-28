"""Unit tests for anomaly detection (risk rules)."""

from backend.observers.anomaly_detector import (
    detect_credit_utilization,
    detect_high_emi_burden,
    detect_large_debit,
    detect_large_credit,
    detect_liquidity_drop,
    detect_unusual_spending,
)

ACCOUNTS = [
    {"account_id": "ACC001", "account_name": "HDFC Savings", "account_type": "SAVINGS", "opening_balance": 100000},
    {"account_id": "ACC002", "account_name": "ICICI Card", "account_type": "CREDIT_CARD", "opening_balance": 20000},
]


def _txn(amount, type="DEBIT", account="ACC001", category="FOOD", desc="x"):
    return {"txn_id": "T", "account_id": account, "date": "2026-08-01", "description": desc,
            "amount": amount, "type": type, "category": category}


def test_large_debit_detected():
    signals = detect_large_debit([_txn(60000)], threshold=50000)
    assert len(signals) == 1
    assert signals[0]["category"] == "LARGE_DEBIT"
    assert signals[0]["severity"] == "MEDIUM"


def test_large_debit_critical_when_double_threshold():
    signals = detect_large_debit([_txn(120000)], threshold=50000)
    assert signals[0]["severity"] == "HIGH"


def test_small_debit_ignored():
    assert detect_large_debit([_txn(500)], threshold=50000) == []


def test_large_credit_detected():
    signals = detect_large_credit([_txn(70000, type="CREDIT")], threshold=50000)
    assert len(signals) == 1
    assert signals[0]["category"] == "LARGE_CREDIT"


def test_liquidity_drop():
    positions = detect_liquidity_drop(
        [{"account_id": "ACC001", "account_name": "H", "account_type": "SAVINGS", "opening_balance": 20000}],
        [],
        min_balance=25000,
    )
    assert len(positions) == 1
    assert positions[0]["severity"] == "HIGH"


def test_liquidity_credit_card_skipped():
    signals = detect_liquidity_drop(ACCOUNTS, [], min_balance=25000)
    # ACC001 (100k) fine, ACC002 is a credit card -> skipped
    assert signals == []


def test_high_emi_burden():
    txns = [_txn(30000, category="LOAN_EMI", desc="EMI - HDFC")]
    signals = detect_high_emi_burden(txns, monthly_income=50000, ratio_threshold=0.5)
    assert len(signals) == 1
    assert signals[0]["severity"] == "HIGH"


def test_unusual_spending():
    signals = detect_unusual_spending([_txn(10000), _txn(200)], avg_daily=500, threshold_ratio=3)
    assert len(signals) == 1
    assert signals[0]["amount"] == 10000


def test_credit_utilization():
    accounts = [{"account_id": "X", "account_type": "CREDIT_CARD", "opening_balance": 200000}]
    signals = detect_credit_utilization(accounts, utilization_threshold=0.7)
    assert len(signals) == 1

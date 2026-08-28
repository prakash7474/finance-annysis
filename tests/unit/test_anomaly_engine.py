"""Unit tests for the transaction anomaly engine."""

from anomaly_engine import compute_category_stats, detect_transaction_anomalies


def _txn(amount, cat="FOOD", txn_id="T"):
    return {"txn_id": txn_id, "category": cat, "amount": amount, "type": "DEBIT"}


def test_normal_transactions_no_anomaly():
    txns = [_txn(300, "FOOD", "A"), _txn(450, "FOOD", "B"), _txn(550, "FOOD", "C"), _txn(600, "FOOD", "D")]
    assert detect_transaction_anomalies(txns) == []


def test_large_transaction_anomaly():
    txns = [_txn(300, "FOOD"), _txn(450, "FOOD"), _txn(550, "FOOD"),
            _txn(600, "FOOD"), _txn(8000, "FOOD", "BIG")]
    anomalies = detect_transaction_anomalies(txns, z_threshold=1.5)
    assert any(a.transaction_id == "BIG" for a in anomalies)
    big = next(a for a in anomalies if a.transaction_id == "BIG")
    assert big.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert big.category == "FOOD"


def test_category_specific_anomaly():
    txns = [_txn(300, "FOOD"), _txn(450, "FOOD"), _txn(550, "FOOD"),
            _txn(600, "FOOD"), _txn(400, "SHOPPING")]
    # Filtering to SHOPPING (only one sample < min_count) -> no anomalies.
    assert detect_transaction_anomalies(txns, category="SHOPPING") == []
    # The food outlier from a SHOPPING-filtered view is not present.
    assert detect_transaction_anomalies(txns, category="FOOD") == []


def test_zero_and_negative_amounts_handled():
    txns = [_txn(0, "FOOD"), _txn(-100, "FOOD"), _txn(-50, "FOOD")]
    # Non-positive amounts are ignored and never raise.
    assert detect_transaction_anomalies(txns) == []
    # Baseline computed only from valid amounts.
    stats = compute_category_stats(txns)
    assert stats == {}


def test_empty_transaction_list():
    assert detect_transaction_anomalies([]) == []


def test_insufficient_baseline_skipped():
    txns = [_txn(100, "FOOD"), _txn(200, "FOOD"), _txn(5000, "FOOD")]
    # Only 3 samples < min_count -> no anomaly.
    assert detect_transaction_anomalies(txns, min_count=4) == []

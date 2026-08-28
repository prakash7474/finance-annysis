"""
anomaly_engine.py - Deterministic statistical transaction anomaly detection.

Baseline is computed per category from positive transaction amounts
(mean + standard deviation) and a new transaction is flagged when it deviates
strongly from that baseline.  Original transaction data is never mutated.

Severity is derived from the z-score of the deviation.
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

from models.financial_models import TransactionAnomaly


def compute_category_stats(transactions: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Compute per-category mean/std/count over positive amounts."""
    groups: Dict[str, List[float]] = {}
    for t in transactions:
        amount = float(t.get("amount") or 0)
        if amount <= 0:
            continue  # ignore invalid / non-positive amounts for the baseline
        cat = t.get("category") or "UNCATEGORIZED"
        groups.setdefault(cat, []).append(amount)

    stats: Dict[str, Dict[str, float]] = {}
    for cat, values in groups.items():
        mean = statistics.fmean(values)
        std = statistics.pstdev(values) if len(values) > 1 else 0.0
        stats[cat] = {"count": float(len(values)), "mean": mean, "std": std}
    return stats


def _severity_from_z(z: float) -> str:
    """Map a |z-score| to a severity. Only called for flagged (z >= threshold)."""
    if z >= 6.0:
        return "CRITICAL"
    if z >= 4.0:
        return "HIGH"
    if z >= 3.0:
        return "MEDIUM"
    return "LOW"


def detect_transaction_anomalies(
    transactions: List[Dict[str, Any]],
    category: Optional[str] = None,
    z_threshold: float = 2.0,
    min_count: int = 4,
) -> List[TransactionAnomaly]:
    """Return anomalous transactions against their category baseline.

    - Empty transaction list -> [] (no crash, no result).
    - Non-positive amounts are never flagged and never poison the baseline.
    - A transaction is flagged only when |z| >= ``z_threshold`` and its
      category has at least ``min_count`` samples.
    """
    if not transactions:
        return []

    stats = compute_category_stats(transactions)
    anomalies: List[TransactionAnomaly] = []

    for t in transactions:
        amount = float(t.get("amount") or 0)
        if amount <= 0:
            continue
        txn_cat = t.get("category") or "UNCATEGORIZED"
        if category and txn_cat != category:
            continue
        stat = stats.get(txn_cat)
        if not stat or stat["count"] < min_count:
            continue

        mean = stat["mean"]
        std = stat["std"]
        if mean <= 0:
            continue

        z = (amount - mean) / std if std else 0.0
        deviation_pct = ((amount - mean) / mean) * 100.0

        if abs(z) < z_threshold:
            continue

        sev = _severity_from_z(abs(z))
        anomalies.append(TransactionAnomaly(
            transaction_id=str(t.get("txn_id") or t.get("id") or "unknown"),
            amount=round(amount, 2),
            category=txn_cat,
            expected_amount=round(mean, 2),
            deviation_percentage=round(deviation_pct, 2),
            severity=sev,
            reason=(
                f"{txn_cat} amount {amount:,.2f} deviates {deviation_pct:+.1f}% "
                f"from the expected {mean:,.2f} (z={z:.2f})."
            ),
        ))

    # Highest severity first (CRITICAL > HIGH > MEDIUM > LOW).
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    anomalies.sort(key=lambda a: severity_rank.get(a.severity, 9))
    return anomalies

"""
alert_engine.py - Smart alert engine.

Consolidates signals from the anomaly, forecast, health, goal, debt and market
watchers into a single, priority-ordered list of financial alerts.  All inputs
must already be structured facts (deterministic) - no arithmetic here.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from models.alert_models import FinancialAlert

SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
LIQUIDITY_MIN = 25000.0


def _alert(category: str, severity: str, title: str, description: str, source: str,
           recommended_action: Optional[str] = None, trace_id: Optional[str] = None) -> FinancialAlert:
    return FinancialAlert(
        alert_id=f"ALT_{uuid.uuid4().hex[:10]}",
        trace_id=trace_id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        category=category, severity=severity, title=title,
        description=description, source=source, recommended_action=recommended_action,
    )


def generate_financial_alerts(facts: Dict[str, Any], trace_id: Optional[str] = None) -> List[FinancialAlert]:
    """Build financial alerts from deterministic facts."""
    alerts: List[FinancialAlert] = []

    # Transaction anomalies
    for anomaly in facts.get("anomalies", []):
        if anomaly.get("severity") in ("MEDIUM", "HIGH", "CRITICAL"):
            alerts.append(_alert(
                "TRANSACTION_ANOMALY", anomaly["severity"],
                f"Unusual transaction in {anomaly.get('category', 'N/A')}",
                anomaly.get("reason", "Transaction deviates from normal."),
                "anomaly_engine", "Review and verify the transaction.", trace_id,
            ))

    # Cash-flow forecast / liquidity
    forecast = facts.get("forecast") or {}
    expected_balance = forecast.get("projected_balance")
    if forecast.get("risk_level") in ("HIGH", "CRITICAL"):
        alerts.append(_alert(
            "FORECAST_RISK", forecast["risk_level"],
            "Projected cash position is risky",
            f"Projected balance in {forecast.get('days', 30)} days is "
            f"{expected_balance:,.2f} with {forecast.get('confidence', 0):.1f} confidence.",
            "forecast_engine", "Build a liquidity buffer; consider reducing expenses.", trace_id,
        ))
    if expected_balance is not None and expected_balance < LIQUIDITY_MIN:
        alerts.append(_alert(
            "LOW_LIQUIDITY", "HIGH" if expected_balance < 0 else "MEDIUM",
            "Projected liquidity is low",
            f"Projected balance {expected_balance:,.2f} is below the {LIQUIDITY_MIN:,.0f} threshold.",
            "forecast_engine", "Build a cash buffer before new commitments.", trace_id,
        ))

    # Health / DTI
    health = facts.get("health") or {}
    dti = facts.get("dti")
    if dti is not None and dti > 0.5:
        alerts.append(_alert("HIGH_DTI", "CRITICAL", "Debt-to-income ratio is critical",
                             f"DTI is {dti * 100:.1f}% (over 50%).", "health_engine",
                             "Avoid additional borrowing; focus on debt reduction.", trace_id))
    elif dti is not None and dti > 0.4:
        alerts.append(_alert("HIGH_DTI", "HIGH", "Debt-to-income ratio is elevated",
                             f"DTI is {dti * 100:.1f}% (40-50%).", "health_engine",
                             "Consider a shorter tenure or lower EMI.", trace_id))
    if health.get("status") in ("AT_RISK", "CRITICAL"):
        alerts.append(_alert("HEALTH_RISK", health.get("status", "HIGH"),
                             f"Financial health is {health.get('status', 'degraded').replace('_', ' ').title()}",
                             f"Health score {health.get('score', 'N/A')}/100.",
                             "health_engine", "Review the contributing factors.", trace_id))

    # Net cash liquidity
    net_cash = facts.get("net_cash")
    if net_cash is not None and net_cash < LIQUIDITY_MIN:
        alerts.append(_alert("LOW_LIQUIDITY", "HIGH" if net_cash < 0 else "MEDIUM",
                             "Liquidity threshold breached",
                             f"Current net cash {net_cash:,.2f} is below {LIQUIDITY_MIN:,.0f}.",
                             "risk_observer", "Build an emergency reserve.", trace_id))

    # Spending spikes
    for s in facts.get("spending", []):
        if s.get("risk_level") == "HIGH":
            alerts.append(_alert("SPENDING_SPIKE", "HIGH",
                                 f"Spending spike in {s.get('category', 'N/A')}",
                                 f"Projected spend is {s.get('projected_amount', 0):,.2f} "
                                 f"({s.get('change_percentage', 0):+.1f}%).",
                                 "forecast_engine", "Review discretionary spending.", trace_id))

    # Goal shortfall
    for goal in facts.get("goals", []):
        shortfall = goal.get("monthly_shortfall", 0)
        if shortfall and shortfall > 0:
            alerts.append(_alert("GOAL_SHORTFALL", "MEDIUM",
                                 f"Goal shortfall: {goal.get('name', 'Savings goal')}",
                                 f"Need {shortfall:,.2f} more per month to reach the goal.",
                                 "goal_engine", "Increase monthly savings or extend the timeline.", trace_id))

    # Market changes
    for m in facts.get("market_alerts", []):
        alerts.append(_alert("MARKET_CHANGE", m.get("severity", "LOW"),
                             f"{m.get('symbol', '?')} {m.get('alert_type', 'change')}",
                             m.get("message", "Market state changed."),
                             "portfolio_watcher", None, trace_id))

    # Debt risk
    for debt in facts.get("debt", []):
        if "HIGH_INTEREST_RATE" in debt.get("reason_codes", []):
            alerts.append(_alert("DEBT_RISK", "MEDIUM",
                                 "High-interest debt present",
                                 f"{debt.get('bank', 'Loan')} carries a high interest rate.",
                                 "debt_optimizer", "Consider prepaying the highest-cost debt.", trace_id))

    # Priority ordering.
    alerts.sort(key=lambda a: SEVERITY_RANK.get(a.severity, 9))
    return alerts

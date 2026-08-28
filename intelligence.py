"""
intelligence.py - Wires the Phase 5 engines to the bank data.

This is a pure, deterministic assembly function: feed it accounts + transactions
(+ optional loan offers / goals) and it returns the full set of structured facts
(health, anomalies, forecast, spending, debt, recommendations, alerts, market
watch, snapshot).  It is reused by the FastAPI layer, the CLI, the MCP server and
the tests so there is exactly one source of Phase 5 logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import finance_engine as fe
import loan_engine as le
from anomaly_engine import detect_transaction_anomalies
from debt_optimizer import optimize_debt
from digital_twin import simulate_financial_scenario
from forecast_engine import (
    forecast_cash_flow,
    forecast_spending,
)
from goal_engine import plan_financial_goal
from health_engine import compute_financial_health
from models.financial_models import DebtInput, FinancialSnapshot
from models.scenario_models import ScenarioInput
from portfolio_watcher import DEFAULT_SYMBOLS, watch_portfolio
from recommendation_engine import generate_recommendations
from alert_engine import generate_financial_alerts

INCOME_CATS = {"SALARY", "FREELANCE", "INTEREST", "DIVIDEND"}


def _active_month(transactions: List[Dict[str, Any]]) -> str:
    if not transactions:
        return "2026-08-01"
    latest = max(t["date"] for t in transactions)
    return latest[:7] + "-01"


def _compute_baseline(accounts: List[Dict[str, Any]], transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    pos = fe.compute_cash_position(accounts, transactions)
    month_start = _active_month(transactions)
    month_end = month_start[:8] + "31"

    def in_month(t: Dict[str, Any]) -> bool:
        return month_start <= t["date"] <= month_end

    income = sum(t["amount"] for t in transactions
                 if in_month(t) and t["type"] == "CREDIT" and t.get("category") in INCOME_CATS)

    # Recurring EMI (deduped by lender) and monthly expenses (non-EMI debits).
    emi_by_lender: Dict[str, float] = {}
    total_debit = 0.0
    emi_debit_total = 0.0
    for t in transactions:
        if not in_month(t) or t["type"] != "DEBIT":
            continue
        total_debit += float(t.get("amount") or 0)
        if t.get("category") == "LOAN_EMI" or "EMI" in str(t.get("description", "")).upper():
            desc = str(t.get("description", "")).split(" - ", 1)
            lender = desc[1].strip() if len(desc) > 1 else str(t.get("description", "UNKNOWN"))
            emi_by_lender[lender] = float(t.get("amount") or 0)

    recurring_emi = round(sum(emi_by_lender.values()), 2)
    # Expenses = non-EMI, non-transfer debits (transfers are not real spending).
    non_emi_debit = 0.0
    for t in transactions:
        if not (in_month(t) and t["type"] == "DEBIT"):
            continue
        cat = t.get("category")
        if cat == "LOAN_EMI" or cat == "TRANSFER":
            continue
        non_emi_debit += float(t.get("amount") or 0)
    expenses = max(0.0, round(non_emi_debit, 2))
    dti = le.calculate_dti(income, recurring_emi)
    return {
        "month": month_start,
        "monthly_income": round(income, 2),
        "monthly_expenses": expenses,
        "existing_emi": recurring_emi,
        "net_cash": pos["net_cash"],
        "dti": dti,
        "accounts": pos["accounts"],
    }


def _debt_items(loan_offers: List[Dict[str, Any]]) -> List[DebtInput]:
    items = []
    for offer in loan_offers:
        items.append(DebtInput(
            loan_id=offer.get("offer_id", "LOAN"),
            bank=offer.get("bank", "Bank"),
            principal=min(offer.get("min_amount", 50000), 400000),
            interest_rate=offer.get("interest_rate", 12.0),
            tenure_months=offer.get("tenure_months", 36),
            existing_monthly_emi=0.0,
        ))
    return items


def compute_phase5_facts(
    accounts: List[Dict[str, Any]],
    transactions: List[Dict[str, Any]],
    loan_offers: Optional[List[Dict[str, Any]]] = None,
    forecast_days: int = 30,
    goals: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute the full Phase 5 fact set deterministically."""
    loan_offers = loan_offers or []
    baseline = _compute_baseline(accounts, transactions)
    income = baseline["monthly_income"]
    existing_emi = baseline["existing_emi"]
    net_cash = baseline["net_cash"]
    expenses = baseline["monthly_expenses"]
    dti = baseline["dti"] if baseline["dti"] is not None else 0.0

    # Health (Phase 5 deterministic score).
    health = compute_financial_health(
        monthly_income=income, monthly_expenses=expenses,
        existing_emi=existing_emi, net_cash=net_cash,
    )

    # Anomaly detection (on debits).
    anomalies = detect_transaction_anomalies(transactions)
    anomalies = [a.model_dump() for a in anomalies]

    # Forecasts.
    forecast = forecast_cash_flow(net_cash, income, expenses, existing_emi, forecast_days)
    spending = forecast_spending(transactions, days=forecast_days, monthly_income=income)
    spending = [s.model_dump() for s in spending]

    # Debt optimization.
    debt_items = _debt_items(loan_offers)
    debt = optimize_debt(debt_items, income, existing_emi, "LOWEST_TOTAL_COST")
    debt = [r.model_dump() for r in debt]

    # Goals (default demonstration goal if none provided).
    if not goals:
        goals = [{
            "target_amount": 200000, "current_saved_amount": 40000, "months_remaining": 8,
            "monthly_income": income, "monthly_expenses": expenses, "monthly_emi": existing_emi,
            "name": "Emergency Fund",
        }]
    goal_results = []
    for g in goals:
        result = plan_financial_goal(
            target_amount=g["target_amount"], current_saved_amount=g["current_saved_amount"],
            months_remaining=g["months_remaining"], monthly_income=g.get("monthly_income", income),
            monthly_expenses=g.get("monthly_expenses", expenses), monthly_emi=g.get("monthly_emi", existing_emi),
            name=g.get("name", "Savings Goal"), goal_id=g.get("goal_id"),
        )
        goal_results.append(result.model_dump())

    # Market watch.
    market = watch_portfolio(DEFAULT_SYMBOLS)
    market_alerts = [a.model_dump() for a in market["alerts"]]

    # Assemble intermediate facts for recommendations/alerts.
    shortfall = max((g["monthly_shortfall"] for g in goal_results), default=0.0)
    facts: Dict[str, Any] = {
        "monthly_income": income,
        "monthly_expenses": expenses,
        "existing_emi": existing_emi,
        "net_cash": net_cash,
        "dti": round(dti, 4),
        "health": health,
        "anomalies": anomalies,
        "forecast": forecast.model_dump(),
        "spending": spending,
        "goals": goal_results,
        "debt": debt,
        "market_alerts": market_alerts,
        "goal_shortfall": round(shortfall, 2),
    }

    recommendations = generate_recommendations(facts)
    recommendations = [r.model_dump() for r in recommendations]
    alerts = generate_financial_alerts(facts)
    alerts = [a.model_dump() for a in alerts]

    # Digital twin baseline snapshot.
    snapshot = FinancialSnapshot(
        monthly_income=income, monthly_expenses=expenses, existing_emi=existing_emi,
        net_cash=net_cash, dti=round(dti, 4), new_emi=0.0,
        cash_flow=round(income - expenses - existing_emi, 2),
        health_score=health["score"], risk_level=health["status"],
    )

    return {
        **baseline,
        "dti": round(dti, 4),
        "health": health,
        "anomalies": anomalies,
        "forecast": forecast.model_dump(),
        "spending": spending,
        "debt": debt,
        "goals": goal_results,
        "market_watch": market["snapshot"],
        "market_alerts": market_alerts,
        "recommendations": recommendations,
        "alerts": alerts,
        "snapshot": snapshot.model_dump(),
    }


def run_scenario_on_facts(facts: Dict[str, Any], scenario: ScenarioInput) -> Dict[str, Any]:
    """Run the digital twin using the computed baseline facts."""
    snapshot = FinancialSnapshot(**facts["snapshot"])
    result = simulate_financial_scenario(snapshot, scenario)
    return result.model_dump()

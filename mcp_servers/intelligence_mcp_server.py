"""
intelligence_mcp_server.py - Standalone MCP server exposing Phase 5 capabilities.

Tools: detect_transaction_anomalies, forecast_cash_flow, forecast_spending,
calculate_financial_health, plan_financial_goal, optimize_debt,
simulate_financial_scenario, get_financial_alerts, get_recommendations.

Read-only resources: finance://health/current, finance://forecast/*,
finance://spending, finance://alerts, finance://recommendations, finance://goals,
finance://digital-twin/current.

All numerical work stays in the Python engines; MCP only exposes the results.
Runs over stdio by default, or SSE with:  python mcp_servers/intelligence_mcp_server.py --sse --port 9004
"""

import json

from mcp.server.mcpserver import MCPServer

from _common import run_server
from backend._boot import MOCK_DATA_FILE

import intelligence
from anomaly_engine import detect_transaction_anomalies
from debt_optimizer import optimize_debt, all_strategy_rankings
from digital_twin import simulate_financial_scenario
from forecast_engine import forecast_cash_flow, forecast_spending, aggregate_monthly_cash
from goal_engine import plan_financial_goal
from health_engine import compute_financial_health
from models.financial_models import DebtInput
from models.scenario_models import ScenarioInput
from recommendation_engine import generate_recommendations
from alert_engine import generate_financial_alerts

mcp = MCPServer("finance-intelligence", instructions="Phase 5 financial intelligence server")

_DATA = json.loads(MOCK_DATA_FILE.read_text(encoding="utf-8"))
_FACTS = intelligence.compute_phase5_facts(_DATA["accounts"], _DATA["transactions"], _DATA["loan_offers"])


def _json(obj) -> str:
    return json.dumps(obj)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def detect_transaction_anomalies() -> str:
    """Detect anomalous transactions using statistical deviation."""
    return _json({"anomalies": _FACTS["anomalies"]})


@mcp.tool()
def forecast_cash_flow(days: int = 30) -> str:
    """Project cash flow over ``days`` (7/14/30/60/90)."""
    f = _FACTS["forecast"]
    fields = ["projected_balance", "projected_income", "projected_expenses", "projected_emi",
              "confidence", "risk_level"]
    return _json({"cash_flow_forecast": {k: f[k] for k in fields}, "days": days})


@mcp.tool()
def forecast_spending(days: int = 30) -> str:
    """Project spending per category over ``days``."""
    return _json({"spending_forecast": _FACTS["spending"]})


@mcp.tool()
def calculate_financial_health() -> str:
    """Return the deterministic financial health score."""
    return _json({"health": {k: _FACTS["health"][k] for k in
                             ("score", "status", "liquidity_score", "debt_score",
                              "expense_score", "savings_score", "reasons")}})


@mcp.tool()
def plan_financial_goal(target_amount: float, current_saved_amount: float, months_remaining: int,
                        monthly_income: float, monthly_expenses: float, monthly_emi: float) -> str:
    """Plan a savings goal (required monthly saving + shortfall)."""
    return _json(plan_financial_goal(target_amount, current_saved_amount, months_remaining,
                                     monthly_income, monthly_expenses, monthly_emi).model_dump())


@mcp.tool()
def optimize_debt(monthly_income: float, existing_emi: float = 0.0) -> str:
    """Rank debt repayment by total cost (LOWEST_TOTAL_COST)."""
    items = [DebtInput(**o) for o in _debt_inputs()]
    recs = optimize_debt(items, monthly_income, existing_emi)
    return _json({"debt_recommendations": [r.model_dump() for r in recs],
                  "all_strategies": all_strategy_rankings(items, monthly_income, existing_emi)})


@mcp.tool()
def simulate_financial_scenario(salary_change_percentage: float = 0.0,
                                expense_change_percentage: float = 0.0,
                                new_loan_amount: float = 0.0,
                                new_loan_rate: float = 12.0,
                                new_loan_tenure: int = 36) -> str:
    """Simulate a financial scenario against the current Digital Twin."""
    from models.financial_models import FinancialSnapshot
    snapshot = FinancialSnapshot(**_FACTS["snapshot"])
    scenario = ScenarioInput(salary_change_percentage=salary_change_percentage,
                             expense_change_percentage=expense_change_percentage,
                             new_loan_amount=new_loan_amount, new_loan_rate=new_loan_rate,
                             new_loan_tenure=new_loan_tenure)
    return _json(simulate_financial_scenario(snapshot, scenario).model_dump())


@mcp.tool()
def get_financial_alerts() -> str:
    """Return the priority-ordered financial alerts."""
    return _json({"alerts": _FACTS["alerts"]})


@mcp.tool()
def get_recommendations() -> str:
    """Return explainable financial recommendations."""
    return _json({"recommendations": _FACTS["recommendations"]})


def _debt_inputs():
    return [DebtInput(loan_id=o["offer_id"], bank=o["bank"],
                      principal=min(o["min_amount"], 400000),
                      interest_rate=o["interest_rate"],
                      tenure_months=o["tenure_months"]).model_dump()
            for o in _DATA["loan_offers"]]


# ── Read-only resources ───────────────────────────────────────────────────────

@mcp.resource("finance://health/current")
def resource_health() -> str:
    return _json(_FACTS["health"])


@mcp.resource("finance://forecast/cashflow")
def resource_cashflow() -> str:
    return _json(_FACTS["forecast"])


@mcp.resource("finance://forecast/spending")
def resource_spending() -> str:
    return _json({"spending": _FACTS["spending"]})


@mcp.resource("finance://alerts")
def resource_alerts() -> str:
    return _json({"alerts": _FACTS["alerts"]})


@mcp.resource("finance://recommendations")
def resource_recommendations() -> str:
    return _json({"recommendations": _FACTS["recommendations"]})


@mcp.resource("finance://goals")
def resource_goals() -> str:
    return _json({"goals": _FACTS["goals"]})


@mcp.resource("finance://digital-twin/current")
def resource_twin() -> str:
    return _json({"snapshot": _FACTS["snapshot"]})


if __name__ == "__main__":
    run_server(mcp, default_port=9004)

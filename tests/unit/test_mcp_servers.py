"""
test_mcp_servers.py - Comprehensive tests for all MCP server tools, resources and error handling.
"""

import json
import pytest

from mcp_servers import (
    bank_mcp_server as bank_mcp,
    market_mcp_server as market_mcp,
    loan_mcp_server as loan_mcp,
    demat_mcp_server as demat_mcp,
    governance_mcp_server as gov_mcp,
    intelligence_mcp_server as intel_mcp,
    market_realtime_mcp_server as mr_mcp,
)


# ── 1. Bank MCP Server ───────────────────────────────────────────────────────

def test_bank_mcp_get_accounts():
    res = bank_mcp.get_accounts()
    data = json.loads(res)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "account_id" in data[0]


def test_bank_mcp_get_transactions():
    res = bank_mcp.get_transactions()
    data = json.loads(res)
    assert isinstance(data, list)
    assert len(data) > 0

    filtered = bank_mcp.get_transactions(account_id="ACC001", start_date="2026-08-01")
    fdata = json.loads(filtered)
    assert isinstance(fdata, list)
    assert all(t["account_id"] == "ACC001" for t in fdata)


def test_bank_mcp_get_loan_offers():
    res = bank_mcp.get_loan_offers()
    data = json.loads(res)
    assert isinstance(data, list)
    assert len(data) > 0


# ── 2. Market MCP Server ─────────────────────────────────────────────────────

def test_market_mcp_get_price():
    res = market_mcp.get_price("RELIANCE")
    data = json.loads(res)
    assert data["symbol"] == "RELIANCE"
    assert data["price"] > 0


def test_market_mcp_get_ohlc():
    res = market_mcp.get_ohlc("INFY", days=10)
    data = json.loads(res)
    assert data["symbol"] == "INFY"
    assert len(data["bars"]) > 0


def test_market_mcp_get_news():
    res = market_mcp.get_news("TCS")
    data = json.loads(res)
    assert data["symbol"] == "TCS"
    assert len(data["news"]) > 0


# ── 3. Loan MCP Server ───────────────────────────────────────────────────────

def test_loan_mcp_calculate_emi():
    res = loan_mcp.calculate_emi(300000, 12.0, 36)
    data = json.loads(res)
    assert "emi" in data
    assert round(data["emi"], 2) == 9964.29


def test_loan_mcp_analyze_loan():
    res = loan_mcp.analyze_loan(300000, 12.0, 36, 120000, 15000)
    data = json.loads(res)
    assert "emi" in data
    assert "total_interest" in data
    assert "risk_level" in data


def test_loan_mcp_compare_loan_offers():
    offers = [
        {"offer_id": "L1", "bank": "HDFC", "interest_rate": 10.5, "tenure_months": 36},
        {"offer_id": "L2", "bank": "ICICI", "interest_rate": 11.5, "tenure_months": 36},
    ]
    # Test JSON string
    res1 = loan_mcp.compare_loan_offers(300000, json.dumps(offers), 100000)
    data1 = json.loads(res1)
    assert isinstance(data1, list)
    assert len(data1) == 2

    # Test pre-parsed list
    res2 = loan_mcp.compare_loan_offers(300000, offers, 100000)
    data2 = json.loads(res2)
    assert len(data2) == 2

    # Test invalid JSON string
    res_err = loan_mcp.compare_loan_offers(300000, "invalid-json", 100000)
    data_err = json.loads(res_err)
    assert "error" in data_err


# ── 4. Demat MCP Server ──────────────────────────────────────────────────────

def test_demat_mcp_order_and_status():
    res = demat_mcp.place_paper_order("ACC_MODERATE", "RELIANCE", "BUY", 10)
    data = json.loads(res)
    assert "order_id" in data or "error" in data

    if "order_id" in data:
        status_res = demat_mcp.get_order_status(data["order_id"])
        status_data = json.loads(status_res)
        assert status_data["order_id"] == data["order_id"]

        resource_res = demat_mcp.resource_order(data["order_id"])
        resource_data = json.loads(resource_res)
        assert resource_data["order_id"] == data["order_id"]


def test_demat_mcp_invalid_inputs():
    res_sym = demat_mcp.place_paper_order("ACC_MODERATE", "INVALID_SYM", "BUY", 10)
    assert json.loads(res_sym)["error"] == "INVALID_SYMBOL"

    res_side = demat_mcp.place_paper_order("ACC_MODERATE", "RELIANCE", "HOLD", 10)
    assert json.loads(res_side)["error"] == "VALIDATION_ERROR"

    res_qty = demat_mcp.place_paper_order("ACC_MODERATE", "RELIANCE", "BUY", -5)
    assert json.loads(res_qty)["error"] == "VALIDATION_ERROR"

    res_nan = demat_mcp.place_paper_order("ACC_MODERATE", "RELIANCE", "BUY", float("nan"))
    assert json.loads(res_nan)["error"] == "VALIDATION_ERROR"


def test_demat_mcp_health_check():
    res = demat_mcp.health_check()
    data = json.loads(res)
    assert data["status"] == "healthy"


# ── 5. Governance MCP Server ─────────────────────────────────────────────────

def test_governance_mcp():
    res_list = gov_mcp.list_accounts()
    data_list = json.loads(res_list)
    assert "accounts" in data_list
    assert len(data_list["accounts"]) > 0

    acc_id = "ACC_CONSERVATIVE"
    res_snap = gov_mcp.get_account_snapshot(acc_id)
    data_snap = json.loads(res_snap)
    assert data_snap["account_id"] == acc_id

    res_res = gov_mcp.resource_snapshot(acc_id)
    assert json.loads(res_res)["account_id"] == acc_id

    res_unknown = gov_mcp.get_account_snapshot("UNKNOWN_ACC")
    assert json.loads(res_unknown)["error"] == "ACCOUNT_NOT_LINKED"

    res_health = gov_mcp.health_check()
    assert json.loads(res_health)["status"] == "healthy"


# ── 6. Intelligence MCP Server ───────────────────────────────────────────────

def test_intelligence_mcp_tools():
    # Test plan_financial_goal without recursion bug
    res_goal = intel_mcp.plan_financial_goal(
        target_amount=200000, current_saved_amount=50000, months_remaining=10,
        monthly_income=120000, monthly_expenses=45000, monthly_emi=15000
    )
    data_goal = json.loads(res_goal)
    assert "required_monthly_saving" in data_goal

    # Test optimize_debt without recursion bug
    res_debt = intel_mcp.optimize_debt(monthly_income=120000, existing_emi=15000)
    data_debt = json.loads(res_debt)
    assert "debt_recommendations" in data_debt

    # Test simulate_financial_scenario without recursion bug
    res_scen = intel_mcp.simulate_financial_scenario(salary_change_percentage=10.0)
    data_scen = json.loads(res_scen)
    assert "simulated" in data_scen

    # Test other intelligence tools
    assert "anomalies" in json.loads(intel_mcp.detect_transaction_anomalies())
    assert "cash_flow_forecast" in json.loads(intel_mcp.forecast_cash_flow(30))
    assert "spending_forecast" in json.loads(intel_mcp.forecast_spending(30))
    assert "health" in json.loads(intel_mcp.calculate_financial_health())
    assert "alerts" in json.loads(intel_mcp.get_financial_alerts())
    assert "recommendations" in json.loads(intel_mcp.get_recommendations())


def test_intelligence_mcp_resources():
    assert "score" in json.loads(intel_mcp.resource_health())
    assert "projected_balance" in json.loads(intel_mcp.resource_cashflow())
    assert "spending" in json.loads(intel_mcp.resource_spending())
    assert "alerts" in json.loads(intel_mcp.resource_alerts())
    assert "recommendations" in json.loads(intel_mcp.resource_recommendations())
    assert "goals" in json.loads(intel_mcp.resource_goals())
    assert "snapshot" in json.loads(intel_mcp.resource_twin())


# ── 7. Market Realtime MCP Server ────────────────────────────────────────────

def test_market_realtime_mcp():
    res_sma = mr_mcp.compute_sma("RELIANCE", window=20)
    data_sma = json.loads(res_sma)
    assert data_sma["symbol"] == "RELIANCE"
    assert "sma" in data_sma

    res_vol = mr_mcp.compute_realized_volatility("RELIANCE", lookback=5)
    data_vol = json.loads(res_vol)
    assert data_vol["symbol"] == "RELIANCE"

    res_trend = mr_mcp.classify_trend("RELIANCE")
    assert "trend" in json.loads(res_trend)

    res_adv = mr_mcp.advance_replay("RELIANCE", steps=2)
    assert json.loads(res_adv)["symbol"] == "RELIANCE"

    res_latest = mr_mcp.resource_latest("RELIANCE")
    assert json.loads(res_latest)["symbol"] == "RELIANCE"

    res_ohlc = mr_mcp.resource_ohlc("RELIANCE")
    assert len(json.loads(res_ohlc)["bars"]) == 30

    res_health = mr_mcp.health_check()
    assert json.loads(res_health)["status"] == "healthy"

"""Unit tests for the Digital Twin (scenario simulator)."""

import loan_engine as le
from digital_twin import simulate_financial_scenario
from models.financial_models import FinancialSnapshot
from models.scenario_models import ScenarioInput


def _base():
    return FinancialSnapshot(
        monthly_income=80000, monthly_expenses=30000, existing_emi=22300, net_cash=50000,
        new_emi=0.0, dti=0.279, cash_flow=27700, health_score=70.0, risk_level="MODERATE")


def test_salary_change_10_percent():
    result = simulate_financial_scenario(_base(), ScenarioInput(salary_change_percentage=-10))
    assert result.simulated.monthly_income == 72000.0
    assert result.simulated.dti > result.baseline.dti
    assert result.scenario_id.startswith("scn")


def test_expenses_increase():
    result = simulate_financial_scenario(_base(), ScenarioInput(expense_change_percentage=15))
    assert result.simulated.monthly_expenses == 34500.0


def test_new_loan_adds_emi():
    result = simulate_financial_scenario(_base(), ScenarioInput(new_loan_amount=200000, new_loan_rate=12, new_loan_tenure=36))
    expected_emi = le.calculate_emi(200000, 12.0, 36)
    assert abs(result.simulated.new_emi - expected_emi) < 0.01
    assert result.simulated.dti > 0.279


def test_combined_scenario():
    result = simulate_financial_scenario(
        _base(), ScenarioInput(salary_change_percentage=-10, expense_change_percentage=15, new_loan_amount=200000))
    assert result.simulated.monthly_income == 72000.0
    assert result.simulated.monthly_expenses == 34500.0
    assert result.simulated.new_emi > 0
    assert result.risk_level in ("MODERATE", "HIGH", "CRITICAL")
    assert len(result.recommendations) > 0


def test_original_data_unchanged():
    base = _base()
    before = base.model_dump()
    simulate_financial_scenario(base, ScenarioInput(salary_change_percentage=-50, new_loan_amount=500000))
    assert base.model_dump() == before  # baseline snapshot was NOT mutated


def test_change_metrics_recorded():
    result = simulate_financial_scenario(_base(), ScenarioInput(salary_change_percentage=-10))
    metrics = [c.metric for c in result.changes]
    assert "monthly_income" in metrics
    assert "dti" in metrics
    assert "health_score" in metrics

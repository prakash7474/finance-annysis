"""Unit tests for the what-if scenario engine."""

import loan_engine as le
from scenario_engine import Scenario, ScenarioDelta, apply_scenario


def test_salary_drop_lowers_income_and_raises_dti():
    scenario = Scenario(monthly_income=80000, existing_emi=22300, net_cash=50000,
                        total_credit=100000, total_debit=60000,
                        loan_amount=300000, loan_rate=12.0, loan_tenure_months=36)
    delta = ScenarioDelta(salary_change_percent=-10)
    result = apply_scenario(scenario, delta)
    assert result["scenario"]["monthly_income"] == 72000.0
    assert result["delta"]["income_change"] == -8000.0
    assert result["scenario"]["dti_ratio"] > result["current"]["dti_ratio"]


def test_emi_matches_engine():
    scenario = Scenario(monthly_income=80000, existing_emi=22300, net_cash=50000,
                        total_credit=100000, total_debit=60000,
                        loan_amount=300000, loan_rate=12.0, loan_tenure_months=36)
    result = apply_scenario(scenario, ScenarioDelta())
    expected = le.calculate_emi(300000, 12.0, 36)
    assert abs(result["current"]["emi"] - expected) < 0.01


def test_loan_amount_change():
    scenario = Scenario(monthly_income=80000, existing_emi=22300, net_cash=50000,
                        total_credit=100000, total_debit=60000,
                        loan_amount=300000, loan_rate=12.0, loan_tenure_months=36)
    result = apply_scenario(scenario, ScenarioDelta(loan_amount=200000))
    assert result["scenario"]["loan_amount"] == 200000
    assert result["scenario"]["emi"] < result["current"]["emi"]


def test_large_expense_reduces_cash():
    scenario = Scenario(monthly_income=80000, existing_emi=0, net_cash=100000,
                        total_credit=100000, total_debit=60000)
    result = apply_scenario(scenario, ScenarioDelta(large_expense=40000))
    assert result["scenario"]["remaining_cash"] == 60000


def test_health_reflects_stress():
    scenario = Scenario(monthly_income=40000, existing_emi=25000, net_cash=10000,
                        total_credit=40000, total_debit=45000,
                        loan_amount=400000, loan_rate=12.0, loan_tenure_months=36)
    result = apply_scenario(scenario, ScenarioDelta(salary_change_percent=-20))
    assert result["scenario"]["health_score"] < result["current"]["health_score"]


def test_no_changes_is_same():
    scenario = Scenario(monthly_income=80000, existing_emi=22300, net_cash=50000,
                        total_credit=100000, total_debit=60000,
                        loan_amount=300000, loan_rate=12.0, loan_tenure_months=36)
    result = apply_scenario(scenario, ScenarioDelta())
    assert result["scenario"]["monthly_income"] == scenario.monthly_income
    assert result["delta"]["income_change_percent"] == 0.0

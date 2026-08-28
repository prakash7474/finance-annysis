"""Unit tests for the goal planner engine."""

from goal_engine import plan_financial_goal


def test_target_and_required_savings():
    goal = plan_financial_goal(200000, 40000, 8, 90000, 25000, 15000)
    assert goal.remaining_amount == 160000
    assert goal.required_monthly_saving == 20000
    assert goal.months_remaining == 8


def test_shortfall_detected():
    goal = plan_financial_goal(200000, 40000, 8, 80000, 40000, 25000)
    assert goal.current_saving_capacity == 15000
    assert goal.monthly_shortfall == 5000
    assert goal.status == "SHORTFALL"


def test_completed_goal():
    goal = plan_financial_goal(200000, 200000, 8, 80000, 30000, 15000)
    assert goal.status == "COMPLETED"
    assert goal.remaining_amount == 0


def test_invalid_target():
    goal = plan_financial_goal(0, 0, 8, 80000, 30000, 15000)
    assert goal.status == "INVALID"
    goal2 = plan_financial_goal(200000, 0, 0, 80000, 30000, 15000)
    assert goal2.status == "INVALID"


def test_on_track():
    goal = plan_financial_goal(200000, 40000, 8, 120000, 30000, 15000)
    assert goal.status == "ON_TRACK"
    assert goal.monthly_shortfall == 0

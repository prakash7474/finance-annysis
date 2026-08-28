"""Unit tests for the recommendation engine."""

from recommendation_engine import generate_recommendations


def test_high_dti_borrowing_warning():
    recs = generate_recommendations({"dti": 0.48, "monthly_income": 80000, "anomalies": [], "spending": []})
    assert any("borrowing" in r.title.lower() for r in recs)
    assert any("HIGH_DTI" in r.reason_codes for r in recs)


def test_low_liquidity_recommendation():
    recs = generate_recommendations({"dti": 0.2, "net_cash": 10000, "anomalies": [], "spending": []})
    assert any("liquidity" in r.title.lower() for r in recs)


def test_goal_shortfall_savings():
    recs = generate_recommendations({"dti": 0.2, "goal_shortfall": 5000, "anomalies": [], "spending": []})
    assert any("savings" in r.title.lower() for r in recs)
    assert any("GOAL_SHORTFALL" in r.reason_codes for r in recs)


def test_priorities_ordered():
    recs = generate_recommendations({"dti": 0.55, "net_cash": 1000, "goal_shortfall": 8000,
                                     "anomalies": [{}], "spending": [{"risk_level": "HIGH"}]})
    priorities = [r.priority for r in recs]
    assert priorities == sorted(priorities)


def test_recommendation_requires_approval_for_borrowing():
    recs = generate_recommendations({"dti": 0.55})
    borrowing = [r for r in recs if r.category == "DEBT"]
    assert borrowing
    assert all(r.requires_approval is True for r in borrowing)


def test_no_issues_fallback():
    recs = generate_recommendations({"dti": 0.1, "net_cash": 100000, "goal_shortfall": 0,
                                     "anomalies": [], "spending": [],
                                     "health": {"status": "HEALTHY", "score": 80}})
    assert len(recs) >= 1
    assert "NO_ISSUES_DETECTED" in recs[0].reason_codes

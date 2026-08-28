"""Phase 5 intelligence APIs (financial health, forecasts, goals, recommendations...)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from approval_engine import ApprovalError, approval_engine
from audit_logger import get_audit, record_decision
from backend.api.deps import get_state
from backend.governance.tracing import new_id
from intelligence import compute_phase5_facts, run_scenario_on_facts
from models.scenario_models import ScenarioInput

router = APIRouter(prefix="/api/finance", tags=["phase5"])

# In-memory stores (modules are imported once; grows within a process).
GOALS: Dict[str, Dict[str, Any]] = {}
RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {}


class GoalCreate(BaseModel):
    target_amount: float = Field(gt=0)
    current_saved_amount: float = Field(default=0.0, ge=0)
    months_remaining: int = Field(gt=0, le=600)
    monthly_income: Optional[float] = None
    monthly_expenses: Optional[float] = None
    monthly_emi: Optional[float] = None
    name: str = "Savings Goal"


async def _facts():
    st = get_state()
    accounts = await st.services.get_accounts()
    transactions = await st.services.get_transactions()
    offers = await st.services.get_loan_offers()
    return compute_phase5_facts(accounts, transactions, offers)


def _trace() -> str:
    return new_id("TRACE").replace("trace_", "")


@router.get("/health")
async def financial_health():
    facts = await _facts()
    health = facts["health"]
    record_decision(_trace(), "financial_health", "success",
                    facts={"score": health["score"], "status": health["status"], "dti": facts["dti"]})
    return {
        **health, "net_cash": facts["net_cash"], "monthly_income": facts["monthly_income"],
        "monthly_expenses": facts["monthly_expenses"], "existing_emi": facts["existing_emi"],
        "dti": facts["dti"],
    }


@router.get("/anomalies")
async def anomalies():
    facts = await _facts()
    return {"anomalies": facts["anomalies"]}


@router.get("/forecast/cashflow")
async def cashflow_forecast(days: int = 30):
    facts = await _facts()
    return facts["forecast"]


@router.get("/forecast/spending")
async def spending_forecast(days: int = 30):
    facts = await _facts()
    return {"spending": facts["spending"]}


@router.get("/goals")
async def list_goals():
    if GOALS:
        return {"goals": list(GOALS.values())}
    facts = await _facts()
    return {"goals": facts["goals"]}


@router.post("/goals", status_code=201)
async def create_goal(body: GoalCreate):
    facts = await _facts()
    from goal_engine import plan_financial_goal

    goal = plan_financial_goal(
        target_amount=body.target_amount,
        current_saved_amount=body.current_saved_amount,
        months_remaining=body.months_remaining,
        monthly_income=body.monthly_income or facts["monthly_income"],
        monthly_expenses=body.monthly_expenses or facts["monthly_expenses"],
        monthly_emi=body.monthly_emi or facts["existing_emi"],
        name=body.name,
    )
    GOALS[goal.goal_id] = goal.model_dump()
    return goal.model_dump()


@router.post("/scenario")
async def run_scenario(body: ScenarioInput):
    facts = await _facts()
    result = run_scenario_on_facts(facts, body)
    trace_id = _trace()
    record_decision(trace_id, "financial_scenario", "success",
                    facts={"simulated_health": result["simulated"]["health_score"],
                           "simulated_dti": result["simulated"]["dti"]},
                    input_summary=body.model_dump())
    return {**result, "trace_id": trace_id}


@router.get("/debt")
async def debt():
    facts = await _facts()
    return {"debt": facts["debt"]}


@router.get("/alerts")
async def alerts():
    facts = await _facts()
    return {"alerts": facts["alerts"]}


@router.get("/recommendations")
async def recommendations():
    facts = await _facts()
    recs = facts["recommendations"]
    for rec in recs:
        RECOMMENDATIONS[rec["recommendation_id"]] = rec
        if rec["recommendation_id"] not in {r["recommendation_id"] for r in approval_engine.list()}:
            rec_model = _to_rec_model(rec)
            approval_engine.submit(rec_model)
    return {"recommendations": recs}


@router.post("/recommendations/{recommendation_id}/approve")
async def approve(recommendation_id: str):
    try:
        result = approval_engine.approve(recommendation_id)
        record_decision(_trace(), "recommendation_approval", "success",
                        recommendation=result, approval_status="APPROVED", execution_status="PENDING")
        return {"success": True, **result}
    except ApprovalError as exc:
        raise HTTPException(status_code=409, detail={"error": exc.code, "message": exc.message})


@router.post("/recommendations/{recommendation_id}/reject")
async def reject(recommendation_id: str):
    try:
        result = approval_engine.reject(recommendation_id)
        record_decision(_trace(), "recommendation_rejection", "success",
                        recommendation=result, approval_status="REJECTED", execution_status="BLOCKED")
        return {"success": True, **result}
    except ApprovalError as exc:
        raise HTTPException(status_code=409, detail={"error": exc.code, "message": exc.message})


@router.get("/audit/{trace_id}")
async def audit(trace_id: str):
    entries = get_audit(trace_id)
    if not entries:
        raise HTTPException(status_code=404, detail={"error": "AUDIT_NOT_FOUND",
                                                     "message": f"No audit trail for {trace_id}."})
    return {"trace_id": trace_id, "audit": entries}


@router.post("/alerts/emit")
async def emit_alerts():
    """Publish the current financial alerts to the SSE stream as ``financial_alert``."""
    from backend.observers.event_bus import EventBus

    facts = await _facts()
    for alert in facts["alerts"]:
        EventBus.publish("financial_alert", alert, severity=alert["severity"])
    return {"success": True, "emitted": len(facts["alerts"])}


@router.post("/narrate")
async def narrate(body: dict):
    """Narrate the current Phase 5 facts (Gemini) or the deterministic fallback."""
    st = get_state()
    facts = await _facts()
    payload = {
        "cash": facts["net_cash"],
        "dti": facts["dti"],
        "health_score": facts["health"]["score"],
        "health_status": facts["health"]["status"],
        "forecast_balance": facts["forecast"]["projected_balance"],
        "alerts": [a["title"] for a in facts["alerts"]],
        "recommendations": [r["title"] for r in facts["recommendations"]],
    }
    text, source = st.narrator.narrate(
        {"domain": "INTELLIGENCE", **payload},
        intent="INTELLIGENCE", user_message=body.get("message", "Summarise my financial health."),
    )
    return {"message": text, "narrator": source, "facts": payload}


def _to_rec_model(rec: dict):
    from models.recommendation_models import Recommendation

    return Recommendation(**rec)

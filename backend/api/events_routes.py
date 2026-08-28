"""
events_routes.py - Server-Sent-Events, alert injection and impact analysis.

``GET /api/events`` streams real-time risk alerts.  The demo injects a large
transaction via ``POST /api/events/inject`` which the RiskObserver processes and
publishes as SSE events; ``POST /api/events/analyze`` recomputes cash, health and
loan affordability after an alert.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import finance_engine as fe
from backend.api.deps import error_response, get_state
from backend.governance.tracing import new_id
from backend.observers.event_bus import EventBus
from backend.schemas.common import StandardErrorCode

router = APIRouter(prefix="/api/events", tags=["events"])


class InjectTxn(BaseModel):
    account_id: str = "ACC001"
    amount: float = Field(gt=0)
    description: str = "LARGE TRANSACTION"
    type: str = "DEBIT"
    category: str = "TRANSFER"
    date: str = "2026-08-28"


class AnalyzeRequest(BaseModel):
    account_id: str = "ACC001"
    amount: float = Field(gt=0)
    event_id: Optional[str] = None


@router.get("")
async def events_stream():
    """Server-Sent Events stream of real-time risk alerts."""

    async def stream():
        queue = EventBus.subscribe()
        trace_id = new_id("trace")
        welcome = {
            "event": "connected",
            "event_id": f"evt_{time.time_ns()}",
            "trace_id": trace_id,
            "severity": "INFO",
            "data": {"message": "Connected to FinPilot event stream."},
        }
        yield f"event: connected\nid: {welcome['event_id']}\ndata: {json.dumps(welcome)}\n\n"
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # comment line keeps the stream open
                    continue
                data = json.dumps(event.get("data", {}))
                yield (f"event: {event.get('event', 'message')}\n"
                       f"id: {event.get('event_id')}\n"
                       f"data: {data}\n\n")
        finally:
            EventBus.unsubscribe(queue)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.get("/recent")
async def recent(limit: int = 40):
    return {"events": EventBus.recent(limit)}


@router.post("/inject")
async def inject_txn(req: InjectTxn):
    st = get_state()
    if st.risk_observer is None:
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Risk observer not initialized.", status_code=503)
    txn = {
        "txn_id": new_id("TXN"),
        "account_id": req.account_id,
        "date": req.date,
        "description": req.description,
        "amount": req.amount,
        "type": req.type,
        "category": req.category,
    }
    events = await _observe(st, txn)
    return {"success": True, "events": [e.model_dump(exclude_none=True) for e in events],
            "snapshot": st.risk_observer.snapshot()}


@router.post("/analyze")
async def analyze_impact(req: AnalyzeRequest):
    """Recompute cash / health / loan affordability after an alert."""
    st = get_state()
    if st.risk_observer is None:
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Risk observer not initialized.", status_code=503)

    snapshot = st.risk_observer.snapshot()

    # Deterministic health & loan affordability impact.
    from health_engine import compute_health_score
    baseline = st.services.baseline
    accounts = await st.services.get_accounts()
    transactions = await st.services.get_transactions()
    summary = fe.summarize_credit_debit(transactions, "2026-08-01", "2026-08-31")

    health = compute_health_score(
        monthly_income=baseline["monthly_income"],
        existing_emi=baseline["existing_emi"],
        net_cash=snapshot["net_cash"],
        total_credit=summary["total_credit"],
        total_debit=summary["total_debit"],
    )

    # Loan affordability: recompute DTI/risk for a reference loan with the new cash.
    import loan_engine as le
    reference_amount = st.session_manager.get_or_create(None, st.services).last_loan_amount or 300000
    loan = le.assess_loan_risk(
        principal=reference_amount, annual_rate_pct=12.0, tenure_months=36,
        monthly_income=baseline["monthly_income"], existing_monthly_emi=baseline["existing_emi"],
    )

    warnings = health.get("warnings", [])
    if snapshot["net_cash"] < 25000:
        warnings.append("Liquidity threshold breached: cash is below ₹25,000.")
    if loan["risk_level"] in ("MEDIUM", "HIGH", "CRITICAL"):
        warnings.append(f"Reference loan affordability risk is {loan['risk_level']}.")

    return {
        "success": True,
        "snapshot": snapshot,
        "health": health,
        "loan_affordability": {
            "amount": reference_amount, "emi": loan["emi"], "dti": loan["emi_income_ratio"],
            "risk_level": loan["risk_level"],
        },
        "risk": {"severity": "HIGH" if snapshot["net_cash"] < 25000 else "MEDIUM", "warnings": warnings},
    }


async def _observe(st, txn: Dict[str, Any]) -> list:
    # Trigger async observe in the worker; RiskObserver is synchronous, so call directly.
    events = st.risk_observer.observe_transaction(txn)
    # Publish a system alert about the injected transaction for the frontend.
    EventBus.publish("system_alert",
                     {"message": "A new transaction was observed by the Risk Observer.",
                      "txn": txn.get("description"), "trace_id": txn.get("txn_id")})
    return events

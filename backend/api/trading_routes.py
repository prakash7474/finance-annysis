"""Trading / allocation API routes (PAPER trading only).

- Market facts come from the accelerated replay feed.
- `/allocate` runs Stage 1 (proposer) + Stage 2 (deterministic Rules Engine);
  the rules engine, not the LLM, has final say.
- `/orders` is paper-only (no live broker path).
- Everything is trace-logged (Phase 5).

Hardened: rate limiting on /allocate, input validation, structured errors, metrics.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from accounts_provider import AccountNotLinked, provider
from allocation_engine import rules_engine
from backend.ai.allocation_proposer import propose_allocation
from backend.api.deps import error_response, get_state
from backend.governance.tracing import new_id
from backend.schemas.common import StandardErrorCode
from demat_engine import InsufficientCash, OrderNotFound, demat_engine
from replay_engine import feed, SYMBOLS
from audit_logger import get_audit, list_audits, record_decision
from structured_logger import get_logger, metrics

log = get_logger("trading_routes")

router = APIRouter(prefix="/api/trading", tags=["trading"])


class AllocateRequest(BaseModel):
    account_id: str = "ACC_CONSERVATIVE"
    symbol: str = "RELIANCE"
    target_pct: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    override_limits: bool = False
    message: Optional[str] = None


class PaperOrderRequest(BaseModel):
    account_id: str = "ACC_CONSERVATIVE"
    symbol: str = "RELIANCE"
    side: str = "BUY"
    quantity: float = Field(gt=0)


@router.get("/accounts")
async def accounts():
    return {"accounts": [s.model_dump() for s in provider.list_snapshots()],
            "note": "Paper trading — simulated accounts"}


@router.get("/accounts/{account_id}")
async def account(account_id: str):
    if not account_id or not isinstance(account_id, str):
        return error_response("VALIDATION_ERROR", "account_id is required", status_code=422)
    try:
        return provider.get_snapshot(account_id).model_dump()
    except AccountNotLinked as exc:
        return error_response(exc.error_code, exc.message, status_code=404)
    except Exception as exc:
        log.exception("account_fetch_error", account_id=account_id)
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Failed to fetch account.",
                              status_code=500)


@router.get("/market/{symbol}/latest")
async def market_latest(symbol: str):
    sym = symbol.upper().strip() if symbol else "RELIANCE"
    if sym not in SYMBOLS:
        return error_response("INVALID_SYMBOL",
                              f"Symbol '{sym}' not in supported list: {SYMBOLS}",
                              status_code=422)
    return feed.market_facts(sym)


@router.get("/market/{symbol}/ohlc")
async def market_ohlc(symbol: str, n: int = 20):
    sym = symbol.upper().strip() if symbol else "RELIANCE"
    if sym not in SYMBOLS:
        return error_response("INVALID_SYMBOL",
                              f"Symbol '{sym}' not in supported list: {SYMBOLS}",
                              status_code=422)
    return {"symbol": sym, "bars": feed.ohlc(sym, n)}


@router.get("/market/{symbol}/sma")
async def market_sma(symbol: str, window: int = 20):
    sym = symbol.upper().strip() if symbol else "RELIANCE"
    if sym not in SYMBOLS:
        return error_response("INVALID_SYMBOL",
                              f"Symbol '{sym}' not in supported list: {SYMBOLS}",
                              status_code=422)
    sma = feed.compute_sma(sym, window)
    if sma is None:
        return error_response("NOT_ENOUGH_DATA", f"Need {window} bars for {sym}.",
                              status_code=422)
    return {"symbol": sym, "sma": sma, "window": window}


@router.get("/market/{symbol}/volatility")
async def market_volatility(symbol: str, lookback: int = 5):
    sym = symbol.upper().strip() if symbol else "RELIANCE"
    if sym not in SYMBOLS:
        return error_response("INVALID_SYMBOL",
                              f"Symbol '{sym}' not in supported list: {SYMBOLS}",
                              status_code=422)
    vol = feed.compute_realized_volatility(sym, lookback)
    if vol is None:
        return error_response("NOT_ENOUGH_DATA", f"Need {lookback + 1} bars for {sym}.",
                              status_code=422)
    return {"symbol": sym, "realized_volatility": vol,
            "spike": feed.detect_volatility_spike(sym)}


@router.get("/trend/{symbol}")
async def market_trend(symbol: str):
    sym = symbol.upper().strip() if symbol else "RELIANCE"
    if sym not in SYMBOLS:
        return error_response("INVALID_SYMBOL",
                              f"Symbol '{sym}' not in supported list: {SYMBOLS}",
                              status_code=422)
    return {"symbol": sym, "trend": feed.classify_trend(sym),
            "price": feed.latest_price(sym)}


@router.post("/allocate")
async def allocate(req: AllocateRequest, request: Request):
    trace_id = new_id("TRACE").replace("trace_", "")

    # Rate limiting on the allocate endpoint (triggers LLM call)
    st = get_state()
    if st.rate_limiter is not None:
        client_key = request.client.host if request.client else "unknown"
        if not st.rate_limiter.allow(f"allocate:{client_key}"):
            metrics.increment("trading_rate_limited")
            log.warning("rate_limited", trace_id=trace_id, client=client_key)
            return error_response(StandardErrorCode.RATE_LIMITED,
                                  "Too many allocation requests. Please wait.",
                                  trace_id=trace_id, status_code=429)

    try:
        snapshot = provider.get_snapshot(req.account_id)
    except AccountNotLinked as exc:
        return error_response(exc.error_code, exc.message, status_code=404)
    except Exception as exc:
        log.exception("snapshot_error", trace_id=trace_id, account_id=req.account_id)
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Failed to fetch account snapshot.",
                              trace_id=trace_id, status_code=500)

    facts = feed.market_facts(req.symbol.upper())
    target_pct = 1.0 if req.override_limits else req.target_pct
    proposal = propose_allocation(snapshot, facts, symbol=req.symbol.upper(), target_pct=target_pct)
    decision = rules_engine.apply(proposal, snapshot, facts["price"], trace_id)

    # Track metrics
    metrics.increment("proposals_made")
    if decision.status == "RESIZED":
        metrics.increment("proposals_rule_adjusted")
    elif decision.status == "REJECTED":
        metrics.increment("proposals_rejected")
    else:
        metrics.increment("proposals_approved")

    log.info("allocation_decision", trace_id=trace_id, account_id=req.account_id,
             symbol=req.symbol.upper(), status=decision.status,
             final_qty=decision.final_quantity, final_value=decision.final_value)

    record_decision(trace_id, "allocation_decision", "success", facts={
        "account_id": req.account_id, "proposal": proposal.model_dump(),
        "rules": [r.model_dump() for r in decision.rules],
        "decision": {k: v for k, v in decision.model_dump().items() if k != "trace_id"},
    }, input_summary={"target_pct": target_pct, "override_limits": req.override_limits,
                      "message": req.message})

    return {
        "trace_id": trace_id,
        "proposal": proposal.model_dump(),
        "decision": decision.model_dump(),
        "market": facts,
        "adjusted_for": [r.rule for r in decision.rules if not r.passed],
    }


@router.post("/orders")
async def place_order(req: PaperOrderRequest):
    trace_id = new_id("TRACE").replace("trace_", "")
    market_price = feed.latest_price(req.symbol.upper())
    try:
        order = demat_engine.place_paper_order(req.account_id, req.symbol.upper(),
                                               req.side, req.quantity, market_price)
    except AccountNotLinked as exc:
        return error_response(exc.error_code, exc.message, status_code=404)
    except InsufficientCash as exc:
        metrics.increment("orders_rejected_insufficient_cash")
        record_decision(trace_id, "paper_order", "rejected", facts={"reason": exc.message})
        return error_response("INSUFFICIENT_CASH", exc.message, status_code=409)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc), status_code=422)
    except Exception as exc:
        log.exception("place_order_error", trace_id=trace_id, account_id=req.account_id)
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Failed to place order.",
                              trace_id=trace_id, status_code=500)

    metrics.increment("orders_filled")
    log.info("paper_order_filled", trace_id=trace_id, order_id=order.order_id,
             account_id=req.account_id, symbol=req.symbol.upper())
    record_decision(trace_id, "paper_order", "success", facts={
        "order": order.model_dump(), "market_price": market_price})
    return {"trace_id": trace_id, "order": order.model_dump(),
            "snapshot": provider.get_snapshot(req.account_id).model_dump()}


@router.get("/orders/{order_id}")
async def order_status(order_id: str):
    try:
        return demat_engine.get_order_status(order_id).model_dump()
    except OrderNotFound as exc:
        return error_response(exc.error_code, exc.message, status_code=404)
    except Exception as exc:
        log.exception("order_status_error", order_id=order_id)
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Failed to fetch order status.",
                              status_code=500)


@router.get("/trace")
async def trace_list(limit: int = 30):
    entries = list_audits(limit)
    trading = [e for e in entries if e.get("operation") in ("allocation_decision", "paper_order")]
    return {"trace_items": trading}


@router.get("/trace/{trace_id}")
async def trace_detail(trace_id: str):
    entries = get_audit(trace_id)
    if not entries:
        return error_response("TRACE_NOT_FOUND", f"No trace for {trace_id}.", status_code=404)
    return {"trace_id": trace_id, "audit": entries}


@router.get("/metrics")
async def trading_metrics():
    """Expose operational counters for the dashboard."""
    return {"metrics": metrics.snapshot()}

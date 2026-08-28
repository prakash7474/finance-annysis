"""
backend/main.py - FinPilot AI Finance Controller HTTP host.

Start:  python backend/main.py
"""

import os
import sys

# Ensure the project root is importable before any backend imports.
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
for _p in (BASE, ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import time  # noqa: E402

import asyncio  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402

from backend import state as app_state  # noqa: E402
from backend.api import (  # noqa: E402
    chat_routes,
    events_routes,
    finance_routes,
    health_routes,
    intelligence_routes,
    loan_routes,
    market_routes,
    trading_routes,
    v6_routes,
    voice_routes,
)
from backend.config import settings  # noqa: E402
from backend.observers.risk_observer import RiskObserver  # noqa: E402
from backend.schemas.common import StandardErrorCode  # noqa: E402

VERSION = "0.4.0"


async def lifespan(app: FastAPI):
    """Start services, connect data sources and seed the risk observer."""
    st = app_state.build()

    # Connect services (MCP or mock) and record component status.
    status_map = await st.services.connect()
    if settings.DATA_SOURCE == "mcp":
        status_map.setdefault("bank", "offline" if status_map.get("bank") == "mock" else "mcp")
        status_map.setdefault("market", "offline" if status_map.get("market") == "mock" else "mcp")

    # Seed the risk observer with current accounts/transactions.
    accounts = await st.services.get_accounts()
    transactions = await st.services.get_transactions()
    st.risk_observer = RiskObserver(accounts=accounts, transactions=transactions)

    st.components_status = {
        "bank": status_map.get("bank", "offline"),
        "market": status_map.get("market", "offline"),
        "loan": "engine",
        "gemini": "configured" if settings.GEMINI_API_KEY else "unavailable",
    }

    # ── Phase: Trading add-on — accelerate the market replay feed and publish
    #    volatility_spike events to the SSE stream when volatility crosses a
    #    threshold (the "AI reacts to a market event" demo beat).
    from replay_engine import feed as replay_feed
    from backend.observers.event_bus import EventBus

    replay_running = True

    async def replay_loop():
        while replay_running:
            replay_feed.advance()
            for sym in replay_feed.symbols:
                if replay_feed.maybe_spike(sym):
                    EventBus.publish("volatility_spike",
                                     {"symbol": sym,
                                      "price": replay_feed.latest_price(sym),
                                      "realized_volatility": replay_feed.compute_realized_volatility(sym)},
                                     severity="HIGH")
            await asyncio.sleep(0.5)

    replay_task = asyncio.create_task(replay_loop())
    yield
    replay_running = False
    replay_task.cancel()
    await st.services.close()


app = FastAPI(title="FinPilot - AI Finance Controller", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak stack traces to the frontend."""
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error_code": StandardErrorCode.INTERNAL_ERROR,
                 "message": "An internal error occurred.", "trace_id": trace_id,
                 "request_id": getattr(request.state, "request_id", None)},
    )


@app.middleware("http")
async def request_ids_middleware(request: Request, call_next):
    from backend.governance.tracing import new_id  # noqa: PLC0415

    request.state.trace_id = getattr(request.state, "trace_id", new_id("trace"))
    request.state.request_id = new_id("req")
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Trace-ID"] = request.state.trace_id
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Duration-Ms"] = f"{int((time.perf_counter() - start) * 1000)}"
    return response


# Mount routers.
app.include_router(health_routes.router)
app.include_router(finance_routes.router)
app.include_router(intelligence_routes.router)
app.include_router(loan_routes.router)
app.include_router(market_routes.router)
app.include_router(chat_routes.router)
app.include_router(voice_routes.router)
app.include_router(events_routes.router)
app.include_router(v6_routes.router)
app.include_router(trading_routes.router)


@app.get("/")
async def root():
    return {"service": "FinPilot AI Finance Controller", "version": VERSION,
            "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=settings.APP_PORT, reload=False)

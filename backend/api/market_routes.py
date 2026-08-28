"""Market API routes."""

from __future__ import annotations

from fastapi import APIRouter

import market_engine as me
from backend.api.deps import error_response, get_state
from backend.orchestrator.data_layer import MarketDataNotFound
from backend.schemas.common import StandardErrorCode
from backend.schemas.market import HighLowRange, MarketQuote, MomentumResult, OHLCResult, TrendResult

router = APIRouter(prefix="/api/market", tags=["market"])


def _not_found(exc: MarketDataNotFound):
    return error_response(StandardErrorCode.MARKET_DATA_NOT_FOUND, exc.args[0] if exc.args else "No market data found.", status_code=404)


@router.get("/price", response_model=MarketQuote)
async def price(symbol: str):
    st = get_state()
    try:
        price = await st.services.get_price(symbol)
    except MarketDataNotFound as exc:
        return _not_found(exc)
    return MarketQuote(symbol=symbol.upper(), price=price)


@router.get("/ohlc", response_model=OHLCResult)
async def ohlc(symbol: str, days: int = 30):
    st = get_state()
    try:
        bars = await st.services.get_ohlc(symbol, days)
    except MarketDataNotFound as exc:
        return _not_found(exc)
    return OHLCResult(symbol=symbol.upper(), bars=bars, count=len(bars))


@router.get("/trend", response_model=TrendResult)
async def trend(symbol: str, sma_days: int = 20):
    st = get_state()
    try:
        bars = await st.services.get_ohlc(symbol, max(sma_days * 2, 60))
    except MarketDataNotFound as exc:
        return _not_found(exc)
    result = me.detect_trend_vs_sma(bars, sma_days=sma_days)
    return TrendResult(symbol=symbol.upper(), sma_days=sma_days, **result)


@router.get("/momentum", response_model=MomentumResult)
async def momentum(symbol: str, lookback_days: int = 10):
    st = get_state()
    try:
        bars = await st.services.get_ohlc(symbol, lookback_days + 5)
    except MarketDataNotFound as exc:
        return _not_found(exc)
    result = me.compute_momentum(bars, lookback_days=lookback_days)
    return MomentumResult(symbol=symbol.upper(), **result)


@router.get("/range", response_model=HighLowRange)
async def high_low(symbol: str, days: int = 20):
    st = get_state()
    try:
        bars = await st.services.get_ohlc(symbol, days + 5)
    except MarketDataNotFound as exc:
        return _not_found(exc)
    result = me.compute_high_low_range(bars, days=days)
    return HighLowRange(**result)

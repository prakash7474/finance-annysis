"""
tool_registry.py - Central, discoverable tool registry.

Every backend capability is registered once.  Routing logic never hard-codes a
tool - it selects tool names from the registry and feeds results (Facts) to the
narrator.  All arithmetic is done by the deterministic Python engines.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional

import finance_engine as fe
import loan_engine as le
import market_engine as me
from backend.governance.validation import (
    ValidationError,
    ensure_positive_int,
    ensure_positive_number,
    ensure_symbol,
)
from backend.orchestrator.context import SessionContext
from backend.orchestrator.data_layer import MarketDataNotFound, Services

# Executor signature: async (services, context, **args) -> dict of facts.
ToolExecutor = Callable[..., Awaitable[Dict[str, Any]]]

# Reference rate used when a query does not state one (deterministic default).
DEFAULT_LOAN_RATE = 12.0


def _month_range(context: SessionContext) -> tuple[str, str]:
    baseline = getattr(context, "services_baseline", None) or {}
    month = baseline.get("month", "2026-08-01")
    return month, month[:8] + "31"


# ──────────────────────────────────────────────────────────────────────────────
# Tool implementations
# ──────────────────────────────────────────────────────────────────────────────

async def _get_cash_position(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    accounts = await services.get_accounts()
    transactions = await services.get_transactions()
    pos = fe.compute_cash_position(accounts, transactions)
    return {"domain": "finance", "net_cash": pos["net_cash"], "accounts": pos["accounts"]}


async def _get_monthly_summary(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    start, end = args.get("start_date"), args.get("end_date")
    if not start or not end:
        start, end = _month_range(ctx)
    transactions = await services.get_transactions(start_date=start, end_date=end)
    summary = fe.summarize_credit_debit(transactions, start, end)
    return {"domain": "finance", **summary}


async def _get_emi_summary(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    start, end = args.get("start_date"), args.get("end_date")
    if not start or not end:
        start, end = _month_range(ctx)
    transactions = await services.get_transactions(start_date=start, end_date=end)
    data = fe.detect_emis(transactions, start, end)
    return {"domain": "finance", "total_emi": data["total_emi"], "emi_count": data["emi_count"],
            "emi_breakdown": data["emi_breakdown"]}


async def _get_category_summary(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    start, end = args.get("start_date"), args.get("end_date")
    if not start or not end:
        start, end = _month_range(ctx)
    transactions = await services.get_transactions(start_date=start, end_date=end)
    cat = fe.get_category_summary(transactions, start, end)
    return {"domain": "finance", "categories": cat["categories"]}


async def _get_financial_baseline(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    accounts = await services.get_accounts()
    transactions = await services.get_transactions()
    pos = fe.compute_cash_position(accounts, transactions)
    baseline = services.baseline
    return {
        "domain": "finance",
        "month": baseline["month"],
        "monthly_income": baseline["monthly_income"],
        "existing_emi": baseline["existing_emi"],
        "net_cash": pos["net_cash"],
        "accounts": pos["accounts"],
    }


async def _calculate_health_score(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    accounts = await services.get_accounts()
    transactions = await services.get_transactions()
    pos = fe.compute_cash_position(accounts, transactions)
    baseline = services.baseline
    start, end = _month_range(ctx)
    summary = fe.summarize_credit_debit(transactions, start, end)
    from health_engine import compute_health_score

    health = compute_health_score(
        monthly_income=baseline["monthly_income"],
        existing_emi=baseline["existing_emi"],
        net_cash=pos["net_cash"],
        total_credit=summary["total_credit"],
        total_debit=summary["total_debit"],
    )
    return {"domain": "finance", "health": health, "monthly_income": baseline["monthly_income"],
            "existing_emi": baseline["existing_emi"], "net_cash": pos["net_cash"]}


async def _calculate_loan(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    amount = ensure_positive_number(args.get("loan_amount", args.get("amount")), "loan amount")
    rate = ensure_positive_number(args.get("rate") if args.get("rate") else DEFAULT_LOAN_RATE, "interest rate")
    tenure = ensure_positive_int(args.get("tenure_months"), "tenure")
    income = float(args.get("monthly_income") or ctx.get("monthly_income") or services.baseline["monthly_income"])
    existing_emi = float(args.get("existing_emi") or ctx.get("existing_emi") or services.baseline["existing_emi"])
    proc_fee = float(args.get("processing_fee_pct") or 0.0)
    result = le.assess_loan_risk(amount, rate, tenure, income, existing_emi, proc_fee)
    dti = le.calculate_dti(income, existing_emi, result["emi"])
    return {"domain": "loan", "loan_amount": amount, "rate": rate, "tenure_months": tenure,
            "monthly_income": income, "existing_emi": existing_emi, **result, "dti": dti}


async def _calculate_emi(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    amount = ensure_positive_number(args.get("amount"), "loan amount")
    rate = ensure_positive_number(args.get("rate") if args.get("rate") else DEFAULT_LOAN_RATE, "interest rate")
    tenure = ensure_positive_int(args.get("tenure_months"), "tenure")
    emi = le.calculate_emi(amount, rate, tenure)
    metrics = le.total_interest_and_cost(amount, rate, tenure)
    return {"domain": "loan", "loan_amount": amount, "rate": rate, "tenure_months": tenure,
            "emi": round(emi, 2), **metrics}


async def _calculate_dti(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    income = float(args.get("monthly_income") or services.baseline["monthly_income"])
    existing_emi = float(args.get("existing_emi") or services.baseline["existing_emi"])
    new_emi = float(args.get("new_emi") or 0.0)
    dti = le.calculate_dti(income, existing_emi, new_emi)
    return {"domain": "loan", "monthly_income": income, "existing_emi": existing_emi,
            "new_emi": new_emi, "dti": dti, "dti_pct": (dti * 100) if dti is not None else None}


async def _get_loan_offers(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    offers = await services.get_loan_offers()
    return {"domain": "loan", "offers": offers}


async def _compare_loan_offers(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    amount = ensure_positive_number(args.get("amount") or ctx.last_loan_amount or 300000, "loan amount")
    income = float(args.get("monthly_income") or services.baseline["monthly_income"])
    existing_emi = float(args.get("existing_emi") or services.baseline["existing_emi"])
    offers = await services.get_loan_offers()
    banks = args.get("banks")
    if banks:
        bank_list = [b.strip().upper() for b in banks if b.strip()]
        offers = [o for o in offers if any(bank in o["bank"].upper() for bank in bank_list)]
    results = le.compare_loan_offers(amount, offers, income, existing_emi)
    return {"domain": "loan", "amount": amount, "monthly_income": income, "existing_emi": existing_emi,
            "offers": results}


async def _get_quote(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    symbol = ensure_symbol(args.get("symbol"))
    ctx.set("last_market_symbol", symbol)
    try:
        price = await services.get_price(symbol)
    except MarketDataNotFound as exc:
        raise ValidationError("MARKET_DATA_NOT_FOUND", exc.args[0] if exc.args else "No market data found.")
    return {"domain": "market", "symbol": symbol, "price": price}


async def _get_ohlc(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    symbol = ensure_symbol(args.get("symbol"))
    days = int(args.get("days") or 30)
    ctx.set("last_market_symbol", symbol)
    try:
        bars = await services.get_ohlc(symbol, days)
    except MarketDataNotFound as exc:
        raise ValidationError("MARKET_DATA_NOT_FOUND", exc.args[0] if exc.args else "No market data found.")
    return {"domain": "market", "symbol": symbol, "bars": bars, "count": len(bars)}


async def _get_trend(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    symbol = ensure_symbol(args.get("symbol"))
    sma_days = int(args.get("sma_days") or 20)
    ctx.set("last_market_symbol", symbol)
    days_needed = max(sma_days * 2, 60)
    try:
        bars = await services.get_ohlc(symbol, days_needed)
    except MarketDataNotFound as exc:
        raise ValidationError("MARKET_DATA_NOT_FOUND", exc.args[0] if exc.args else "No market data found.")
    trend = me.detect_trend_vs_sma(bars, sma_days=sma_days)
    return {"domain": "market", "symbol": symbol, **trend, "sma_days": sma_days}


async def _get_momentum(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    symbol = ensure_symbol(args.get("symbol"))
    lookback = int(args.get("lookback_days") or 10)
    ctx.set("last_market_symbol", symbol)
    try:
        bars = await services.get_ohlc(symbol, lookback + 5)
    except MarketDataNotFound as exc:
        raise ValidationError("MARKET_DATA_NOT_FOUND", exc.args[0] if exc.args else "No market data found.")
    mom = me.compute_momentum(bars, lookback_days=lookback)
    return {"domain": "market", "symbol": symbol, **mom}


async def _run_scenario(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    from scenario_engine import Scenario, ScenarioDelta, apply_scenario

    accounts = await services.get_accounts()
    transactions = await services.get_transactions()
    pos = fe.compute_cash_position(accounts, transactions)
    baseline = services.baseline
    start, end = _month_range(ctx)
    summary = fe.summarize_credit_debit(transactions, start, end)

    scenario = Scenario(
        monthly_income=float(args.get("monthly_income") or baseline["monthly_income"]),
        existing_emi=float(args.get("existing_emi") or baseline["existing_emi"]),
        net_cash=pos["net_cash"],
        total_credit=summary["total_credit"],
        total_debit=summary["total_debit"],
        loan_amount=float(args.get("loan_amount") or 0.0),
        loan_rate=float(args.get("rate") or 0.0),
        loan_tenure_months=int(args.get("tenure_months") or 0),
    )
    delta = ScenarioDelta(
        salary_change_percent=float(args.get("salary_change_percent") or 0.0),
        large_expense=float(args.get("large_expense") or 0.0),
        existing_emi_change_percent=float(args.get("existing_emi_change_percent") or 0.0),
        loan_amount=float(args["loan_amount"]) if args.get("loan_amount") else None,
        loan_rate=float(args["rate"]) if args.get("rate") else None,
        loan_tenure_months=int(args["tenure_months"]) if args.get("tenure_months") else None,
    )
    result = apply_scenario(scenario, delta)
    return {"domain": "loan", "scenario": result}


async def _what_if_tenure(services: Services, ctx: SessionContext, **args) -> Dict[str, Any]:
    amount = ensure_positive_number(args.get("amount"), "loan amount")
    rate = ensure_positive_number(args.get("rate"), "interest rate")
    current_tenure = ensure_positive_int(args.get("current_tenure"), "current tenure")
    proposed_tenure = ensure_positive_int(args.get("proposed_tenure"), "proposed tenure")
    income = float(args.get("monthly_income") or services.baseline["monthly_income"])
    existing_emi = float(args.get("existing_emi") or services.baseline["existing_emi"])
    current = le.assess_loan_risk(amount, rate, current_tenure, income, existing_emi)
    proposed = le.assess_loan_risk(amount, rate, proposed_tenure, income, existing_emi)
    return {"domain": "loan", "current": current, "proposed": proposed,
            "diff": {"emi": round(proposed["emi"] - current["emi"], 2),
                     "interest": round(proposed["total_interest"] - current["total_interest"], 2)}}


# ──────────────────────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────────────────────

class ToolSpec:
    def __init__(self, name: str, domain: str, server: str, description: str, executor: ToolExecutor):
        self.name = name
        self.domain = domain
        self.server = server
        self.description = description
        self.executor = executor

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "domain": self.domain, "server": self.server,
                "description": self.description}


def build_registry() -> Dict[str, ToolSpec]:
    specs = {
        "get_cash_position": ToolSpec("get_cash_position", "finance", "bank", "Current cash position across all accounts.", _get_cash_position),
        "get_monthly_summary": ToolSpec("get_monthly_summary", "finance", "bank", "Monthly credit/debit summary.", _get_monthly_summary),
        "get_emi_summary": ToolSpec("get_emi_summary", "finance", "bank", "EMI breakdown for a period.", _get_emi_summary),
        "get_category_summary": ToolSpec("get_category_summary", "finance", "bank", "Spending by category.", _get_category_summary),
        "get_financial_baseline": ToolSpec("get_financial_baseline", "finance", "bank", "Monthly income, existing EMIs and net cash.", _get_financial_baseline),
        "calculate_health_score": ToolSpec("calculate_health_score", "finance", "engine", "Deterministic financial health score.", _calculate_health_score),
        "calculate_loan": ToolSpec("calculate_loan", "loan", "loan", "EMI, total cost and risk for a loan.", _calculate_loan),
        "calculate_emi": ToolSpec("calculate_emi", "loan", "loan", "EMI for a principal/rate/tenure.", _calculate_emi),
        "calculate_dti": ToolSpec("calculate_dti", "loan", "loan", "Debt-to-income ratio.", _calculate_dti),
        "get_loan_offers": ToolSpec("get_loan_offers", "loan", "loan", "Available loan offers.", _get_loan_offers),
        "compare_loan_offers": ToolSpec("compare_loan_offers", "loan", "loan", "Compare loan offers by cost and risk.", _compare_loan_offers),
        "what_if_tenure": ToolSpec("what_if_tenure", "loan", "loan", "Compare EMI/cost when tenure changes.", _what_if_tenure),
        "run_scenario": ToolSpec("run_scenario", "loan", "loan", "What-if scenario simulation.", _run_scenario),
        "get_quote": ToolSpec("get_quote", "market", "market", "Latest market price.", _get_quote),
        "get_ohlc": ToolSpec("get_ohlc", "market", "market", "OHLC history.", _get_ohlc),
        "get_trend": ToolSpec("get_trend", "market", "market", "Trend vs SMA.", _get_trend),
        "get_momentum": ToolSpec("get_momentum", "market", "market", "Price momentum.", _get_momentum),
    }
    return specs


_REGISTRY: Dict[str, ToolSpec] = build_registry()


def get_registry() -> Dict[str, ToolSpec]:
    return _REGISTRY


def get_tool(name: str) -> Optional[ToolSpec]:
    return _REGISTRY.get(name)


def require_tool(name: str) -> ToolSpec:
    tool = _REGISTRY.get(name)
    if tool is None:
        raise ValidationError("UNKNOWN_TOOL", f"Unknown tool: {name}")
    return tool


def list_tools() -> List[Dict[str, Any]]:
    spec = [s.to_dict() for s in _REGISTRY.values()]
    return sorted(spec, key=lambda x: x["name"])

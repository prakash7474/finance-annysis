"""
orchestrator.py - The central Mediator.

Flow for every request:
  receive message -> session/request/trace ids -> route intent -> discover tools
  -> validate inputs -> invoke deterministic tools (budget-guarded) -> build Facts
  -> Gemini narrator -> respond -> audit.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.config import settings
from backend.governance import tracing
from backend.governance.audit import AuditLog
from backend.governance.budget import BudgetExceeded, OperationalBudgetTracker
from backend.governance.validation import ValidationError
from backend.observers.event_bus import EventBus
from backend.orchestrator import router as intent_router
from backend.orchestrator.context import SessionContext
from backend.orchestrator.data_layer import Services, get_services
from backend.orchestrator.narrator import Narrator, make_narrator
from backend.orchestrator.session import SessionManager
from backend.orchestrator.tool_registry import get_registry, require_tool
from backend.schemas.chat import ChatResponse


class Orchestrator:
    def __init__(self, services: Optional[Services] = None, narrator: Optional[Narrator] = None,
                 session_manager: Optional[SessionManager] = None, emit_events: bool = True):
        self.services = services or get_services()
        self.narrator = narrator or make_narrator()
        self.sessions = session_manager or SessionManager()
        self.registry = get_registry()
        self.emit_events = emit_events

    # ── public entrypoint ───────────────────────────────────────────────────
    async def route(self, message: str, session_id: Optional[str] = None,
                    budget_max_tool_calls: Optional[int] = None,
                    budget_max_cost_usd: Optional[float] = None) -> ChatResponse:
        trace = tracing.Tracer.start(session_id)
        ctx = self.sessions.get_or_create(session_id, self.services)

        intent_result, entities = intent_router.detect_intent(message, ctx)
        trace.step("ROUTER", "detect_intent", "SUCCESS")

        # Store parsed entities into context (loans, symbol, salary change).
        for key in ("loan_amount", "rate", "tenure_months", "symbol", "salary_change_percent"):
            if key in entities:
                ctx.set(f"_parsed_{key}", entities[key])

        # Budget
        budget = OperationalBudgetTracker(max_tool_calls=budget_max_tool_calls,
                                          max_cost_usd=budget_max_cost_usd,
                                          trace_id=trace.trace_id)

        required_tools = intent_result.required_tools
        facts, tool_steps, risk = await self._execute(
            required_tools, entities, ctx, budget, trace
        )
        if risk.get("error_code") == "BUDGET_EXCEEDED":
            tracing.Tracer.end(trace.trace_id, "budget_exceeded")
            return ChatResponse(
                success=False, session_id=ctx.session_id, request_id=trace.request_id,
                trace_id=trace.trace_id, message=risk.get("message", ""),
                intent=intent_result.intent, error_code="BUDGET_EXCEEDED",
                tools_used=[s["name"] for s in tool_steps if s["status"] == "success"],
                facts=facts, risk=risk,
            )

        # Always enrich with baseline facts for narration/multi-domain.
        baseline = self.services.baseline
        if facts.get("baseline") is None:
            facts["baseline"] = {
                "month": baseline.get("month"),
                "monthly_income": baseline.get("monthly_income"),
                "existing_emi": baseline.get("existing_emi"),
            }

        message_text, narrator_source = self.narrator.narrate(
            facts, intent=intent_result.intent, user_message=message, session_id=ctx.session_id,
        )
        trace.step("GEMINI", "narration", "SUCCESS")

        # Persist conversational context.
        self._update_context(ctx, entities, facts)
        ctx.add_message("user", message)
        ctx.add_message("assistant", message_text)

        tracing.Tracer.end(trace.trace_id, "completed")
        AuditLog.record(trace.trace_id, "orchestrator", "route", status="success",
                        session_id=ctx.session_id, request_id=trace.request_id,
                        intent=intent_result.intent, tools=list(tools_used_names(tool_steps)),
                        narrator=narrator_source)

        return ChatResponse(
            success=True, session_id=ctx.session_id, request_id=trace.request_id,
            trace_id=trace.trace_id, message=message_text, intent=intent_result.intent,
            tools_used=list(tools_used_names(tool_steps)), facts=facts, risk=risk,
            narrator=narrator_source,
        )

    # ── tool execution ──────────────────────────────────────────────────────
    async def _execute(self, required_tools: List[str], entities: Dict[str, Any],
                       ctx: SessionContext, budget: OperationalBudgetTracker,
                       trace: tracing.RequestTrace) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
        facts: Dict[str, Any] = {}
        tool_steps: List[Dict[str, Any]] = []
        risk: Dict[str, Any] = {}
        failed_any = False

        for tool_name in required_tools:
            try:
                spec = require_tool(tool_name)
            except ValidationError as exc:
                risk = {"error_code": exc.error_code, "message": exc.message}
                break

            call_id = tracing.new_id("tool")
            args = self._build_args(tool_name, entities, ctx)
            try:
                budget.consume(call_id, tool_name, domain=spec.domain)
            except BudgetExceeded as exc:
                # Stop execution immediately; never continue after budget failure.
                AuditLog.record(trace.trace_id, "budget", "consume", status="budget_exceeded",
                                session_id=ctx.session_id)
                risk = {"error_code": "BUDGET_EXCEEDED", "message": exc.message,
                        "budget": budget.snapshot()}
                return facts, tool_steps, risk

            try:
                from time import monotonic
                start = monotonic()
                result = await spec.executor(self.services, ctx, **args)
                duration_ms = round((monotonic() - start) * 1000, 2)
                tool_steps.append({"name": tool_name, "tool_call_id": call_id, "status": "success",
                                   "domain": spec.domain, "duration_ms": duration_ms})
                trace.step(spec.server.upper(), tool_name, "SUCCESS", duration_ms=duration_ms)
                AuditLog.record(trace.trace_id, spec.server, tool_name, status="success",
                                duration_ms=duration_ms, session_id=ctx.session_id)
                self._aggregate(facts, tool_name, result)
                if self.emit_events:
                    EventBus.publish("tool_step", {"tool": tool_name, "status": "success",
                                                   "domain": spec.domain, "trace_id": trace.trace_id})
            except ValidationError as exc:
                tool_steps.append({"name": tool_name, "tool_call_id": call_id, "status": "failed",
                                   "domain": spec.domain, "error": exc.message})
                trace.step(spec.server.upper(), tool_name, "FAILED")
                failed_any = True
            except Exception as exc:  # noqa: BLE001 - convert to structured failure
                tool_steps.append({"name": tool_name, "tool_call_id": call_id, "status": "failed",
                                   "domain": spec.domain, "error": str(exc)[:200]})
                trace.step(spec.server.upper(), tool_name, "FAILED")
                failed_any = True

        if failed_any and not facts:
            risk = {"error_code": "MCP_ERROR", "message": "A backend tool failed; no results available.",
                    "tools_failed": [s["name"] for s in tool_steps if s["status"] == "failed"]}
        return facts, tool_steps, risk

    def _build_args(self, tool_name: str, entities: Dict[str, Any], ctx: SessionContext) -> Dict[str, Any]:
        # Merge parsed entities with conversation context.
        args: Dict[str, Any] = {}
        defaults = {
            "loan_amount": entities.get("loan_amount") or ctx.last_loan_amount,
            "amount": entities.get("amount") or ctx.last_loan_amount,
            "rate": entities.get("rate") or ctx.last_loan_rate,
            "tenure_months": entities.get("tenure_months") or ctx.last_loan_tenure,
            "symbol": entities.get("symbol") or ctx.last_market_symbol,
            "salary_change_percent": entities.get("salary_change_percent") or 0.0,
        }
        for key, value in defaults.items():
            if value is not None:
                args[key] = value

        # Inject known monthly income / existing EMI where relevant.
        max_needs = ["calculate_loan", "calculate_dti", "compare_loan_offers", "what_if_tenure", "run_scenario"]
        if tool_name in max_needs:
            income = ctx.monthly_income or self.services.baseline.get("monthly_income")
            emi = ctx.existing_emi or self.services.baseline.get("existing_emi")
            if income is not None:
                args.setdefault("monthly_income", income)
            if emi is not None:
                args.setdefault("existing_emi", emi)
        return args

    def _aggregate(self, facts: Dict[str, Any], tool_name: str, result: Dict[str, Any]) -> None:
        domain = result.get("domain")
        facts["domain"] = domain
        if tool_name == "get_cash_position":
            facts["cash_position"] = {"net_cash": result.get("net_cash"), "accounts": result.get("accounts")}
        elif tool_name == "get_financial_baseline":
            facts["baseline"] = {
                "month": result.get("month"), "monthly_income": result.get("monthly_income"),
                "existing_emi": result.get("existing_emi"), "net_cash": result.get("net_cash"),
            }
            facts["cash_position"] = {"net_cash": result.get("net_cash"), "accounts": result.get("accounts")}
        elif tool_name == "get_monthly_summary":
            facts["monthly_summary"] = {k: result.get(k) for k in
                                        ("total_credit", "total_debit", "net_change", "transaction_count")}
        elif tool_name == "get_emi_summary":
            facts["emi_summary"] = {"total_emi": result.get("total_emi"), "emi_count": result.get("emi_count")}
        elif tool_name == "get_category_summary":
            facts["categories"] = result.get("categories")
        elif tool_name == "calculate_health_score":
            facts["health"] = result.get("health")
            facts["cash_position"] = {"net_cash": result.get("net_cash"), "accounts": []}
        elif tool_name == "calculate_loan":
            facts["loan"] = {
                "amount": result.get("loan_amount"), "rate": result.get("rate"),
                "tenure_months": result.get("tenure_months"), "emi": result.get("emi"),
                "total_interest": result.get("total_interest"), "total_cost": result.get("total_cost"),
                "emi_income_ratio": result.get("emi_income_ratio"), "dti": result.get("dti"),
                "risk_level": result.get("risk_level"), "risk_flags": result.get("risk_flags"),
            }
        elif tool_name == "calculate_dti":
            facts["loan"] = {**facts.get("loan", {}), "dti": result.get("dti"),
                             "master_dti": result.get("dti")}
        elif tool_name == "calculate_emi":
            facts["loan_metrics"] = result
        elif tool_name == "compare_loan_offers":
            facts["offers"] = result.get("offers")
        elif tool_name == "get_loan_offers":
            facts["available_offers"] = result.get("offers")
        elif tool_name == "run_scenario":
            facts["scenario"] = result.get("scenario")
        elif tool_name == "what_if_tenure":
            facts["tenure_comparison"] = result
        elif domain == "market":
            market = facts.setdefault("market", {})
            if tool_name == "get_quote":
                market.update({"symbol": result.get("symbol"), "price": result.get("price")})
            elif tool_name == "get_trend":
                market.update({"trend": result.get("trend"), "pct_diff": result.get("pct_diff"),
                               "sma_days": result.get("sma_days"), "sma": result.get("sma"),
                               "latest_close": result.get("latest_close")})
            elif tool_name == "get_momentum":
                market.update({"momentum_pct": result.get("momentum_pct"),
                               "lookback_days": result.get("lookback_days")})
            elif tool_name == "get_ohlc":
                market.update({"ohlc_count": result.get("count")})

    def _update_context(self, ctx: SessionContext, entities: Dict[str, Any], facts: Dict[str, Any]) -> None:
        if entities.get("loan_amount") or entities.get("rate") or entities.get("tenure_months"):
            if entities.get("loan_amount"):
                ctx.set("last_loan_amount", float(entities["loan_amount"]))
            if entities.get("rate"):
                ctx.set("last_loan_rate", float(entities["rate"]))
            if entities.get("tenure_months"):
                ctx.set("last_loan_tenure", int(entities["tenure_months"]))
        if entities.get("symbol"):
            ctx.set("last_market_symbol", entities["symbol"])
        baseline = facts.get("baseline")
        if baseline:
            ctx.set("monthly_income", baseline.get("monthly_income"))
            ctx.set("existing_emi", baseline.get("existing_emi"))


def tools_used_names(tool_steps: List[Dict[str, Any]]) -> List[str]:
    return [s["name"] for s in tool_steps if s["status"] == "success"]

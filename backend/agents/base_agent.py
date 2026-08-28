"""Multi-agent framework: base agent + agent context.

Agents communicate only through structured data.  They never mutate global
state or bank data; each agent returns a ``{agent, facts, status, error}``
result that the orchestrator merges.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.governance import tracing
from backend.orchestrator.context import SessionContext
from backend.orchestrator.data_layer import Services


@dataclass
class AgentContext:
    """Everything an agent needs to service a request."""

    services: Services
    session: SessionContext
    trace: tracing.RequestTrace
    entities: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    budget: Any = None  # OperationalBudgetTracker
    cache: Dict[str, Any] = field(default_factory=dict)  # per-request cache (never global)


class BaseAgent:
    name = "base_agent"

    def __init__(self, services: Services):
        self.services = services

    async def handle(self, ctx: AgentContext) -> Dict[str, Any]:
        raise NotImplementedError

    def result(self, facts: Dict[str, Any], status: str = "ok", error: str | None = None) -> Dict[str, Any]:
        return {"agent": self.name, "facts": facts, "status": status, "error": error}

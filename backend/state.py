"""Process-wide application state (singletons) shared by API routes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.config import settings
from backend.governance.rate_limit import RateLimiter
from backend.orchestrator.data_layer import Services
from backend.orchestrator.narrator import Narrator, make_narrator
from backend.orchestrator.orchestrator import Orchestrator
from backend.orchestrator.session import SessionManager


@dataclass
class AppState:
    services: Optional[Services] = None
    orchestrator: Optional[Orchestrator] = None
    narrator: Optional[Narrator] = None
    session_manager: Optional[SessionManager] = None
    rate_limiter: Optional[RateLimiter] = None
    risk_observer: Optional[Any] = None
    components_status: Dict[str, str] = field(default_factory=dict)
    data_source: str = "mock"


state = AppState()


def build(narrator: Optional["Narrator"] = None) -> AppState:
    """Populate and return the shared AppState."""
    global state
    services = Services(settings.DATA_SOURCE)
    narr = narrator if narrator is not None else make_narrator()
    state.services = services
    state.narrator = narr
    state.session_manager = SessionManager()
    state.rate_limiter = RateLimiter()
    state.orchestrator = Orchestrator(services=services, narrator=narr, session_manager=state.session_manager)
    state.data_source = settings.DATA_SOURCE
    return state

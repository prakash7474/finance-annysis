"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from backend import state as app_state
from backend.schemas.common import HealthComponent, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    st = app_state.state
    services = st.components_status or {}

    def component(name, status, detail=None):
        return HealthComponent(name=name, status=status, detail=detail)

    services_out = {
        "bank_mcp": component("bank_mcp", services.get("bank", "offline")),
        "market_mcp": component("market_mcp", services.get("market", "offline")),
        "loan_engine": component("loan_engine", "configured" if _loan_engine() else "offline"),
        "gemini": component("gemini", "configured" if _gemini_configured() else "unavailable"),
        "orchestrator": component("orchestrator", "online" if st.orchestrator else "offline"),
    }
    overall = "healthy" if st.orchestrator else "degraded"
    return HealthResponse(status=overall, services=services_out, version="0.4.0")


def _gemini_configured() -> bool:
    from backend.config import settings
    return bool(settings.GEMINI_API_KEY)


def _loan_engine() -> bool:
    try:
        import loan_engine  # noqa: F401
        return True
    except Exception:
        return False

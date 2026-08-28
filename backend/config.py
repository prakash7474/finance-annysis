"""FinPilot configuration.

All tunables live in the environment (``.env`` file).  No secrets are ever
exposed to the frontend: ``GEMINI_API_KEY`` stays server-side only.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from backend import _boot  # noqa: F401  (ensure project root importable)

load_dotenv()


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Runtime configuration for FinPilot."""

    # ── AI (Gemini) ──────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GEMINI_TIMEOUT_SECONDS: float = _float("GEMINI_TIMEOUT_SECONDS", 20.0)

    # ── Data source / MCP ────────────────────────────────────────────────────
    # "mcp"  -> talk to the MCP servers (auto-spawned stdio or remote SSE)
    # "mock" -> read deterministic mock data directly (reliable offline fallback)
    DATA_SOURCE: str = os.getenv("DATA_SOURCE", "mcp").lower()
    MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio").lower()  # stdio | sse
    MCP_TIMEOUT_SECONDS: float = _float("MCP_TIMEOUT_SECONDS", 5.0)
    MCP_MAX_RETRIES: int = _int("MCP_MAX_RETRIES", 2)

    MCP_DIR: Path = _boot.ROOT / "mcp_servers"
    BANK_MCP_SCRIPT: str = os.getenv("BANK_MCP_SCRIPT", "bank_mcp_server.py")
    MARKET_MCP_SCRIPT: str = os.getenv("MARKET_MCP_SCRIPT", "market_mcp_server.py")
    LOAN_MCP_SCRIPT: str = os.getenv("LOAN_MCP_SCRIPT", "loan_mcp_server.py")

    BANK_MCP_URL: str = os.getenv("BANK_MCP_URL", "http://127.0.0.1:9001/sse")
    MARKET_MCP_URL: str = os.getenv("MARKET_MCP_URL", "http://127.0.0.1:9002/sse")
    LOAN_MCP_URL: str = os.getenv("LOAN_MCP_URL", "http://127.0.0.1:9003/sse")

    MCP_SSE_PORT_BANK: int = _int("MCP_SSE_PORT_BANK", 9001)
    MCP_SSE_PORT_MARKET: int = _int("MCP_SSE_PORT_MARKET", 9002)
    MCP_SSE_PORT_LOAN: int = _int("MCP_SSE_PORT_LOAN", 9003)

    # ── Operational budget guard ─────────────────────────────────────────────
    BUDGET_MAX_TOOL_CALLS: int = _int("BUDGET_MAX_TOOL_CALLS", 8)
    BUDGET_MAX_COST_USD: float = _float("BUDGET_MAX_COST_USD", 0.05)

    # ── Rate limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_MAX_REQUESTS: int = _int("RATE_LIMIT_MAX_REQUESTS", 60)
    RATE_LIMIT_WINDOW_SECONDS: int = _int("RATE_LIMIT_WINDOW_SECONDS", 60)

    # ── Risk observer thresholds ─────────────────────────────────────────────
    RISK_LIQUIDITY_MIN_BALANCE: float = _float("RISK_LIQUIDITY_MIN_BALANCE", 25000.0)
    RISK_LARGE_DEBIT_THRESHOLD: float = _float("RISK_LARGE_DEBIT_THRESHOLD", 50000.0)
    RISK_LARGE_CREDIT_THRESHOLD: float = _float("RISK_LARGE_CREDIT_THRESHOLD", 50000.0)
    RISK_EMI_BURDEN_RATIO: float = _float("RISK_EMI_BURDEN_RATIO", 0.5)
    RISK_CREDIT_UTILIZATION_THRESHOLD: float = _float("RISK_CREDIT_UTILIZATION_THRESHOLD", 0.7)
    RISK_UNUSUAL_SPEND_THRESHOLD: float = _float("RISK_UNUSUAL_SPEND_THRESHOLD", 0.35)

    # ── Application ──────────────────────────────────────────────────────────
    APP_PORT: int = _int("APP_PORT", 8000)
    ENABLE_SSE_EVENTS: bool = _bool("ENABLE_SSE_EVENTS", True)
    # Comma separated list of allowed frontend origins for CORS.
    ALLOWED_ORIGINS: list = [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
    ]


settings = Settings()

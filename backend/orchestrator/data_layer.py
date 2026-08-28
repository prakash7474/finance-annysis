"""
data_layer.py - Backend data access.

Provides ``Services`` which the tools use to fetch bank and market data.
Two source strategies are supported:

  - ``MCP``   : talk to the standalone MCP servers (stdio subprocess or remote SSE)
  - ``mock``  : read deterministic mock data directly (reliable offline fallback)

Each domain (bank / market) independently falls back to mock when its MCP
server is unreachable, so finance features keep working even if the market MCP
is down (and vice-versa).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend import _boot
from backend.config import settings


# ──────────────────────────────────────────────────────────────────────────────
# MCP connection (single persistent session per server)
# ──────────────────────────────────────────────────────────────────────────────

class MCPConn:
    """A persistent MCP client connection to a single server."""

    def __init__(self, name: str, script: str = None, url: str = None, transport: str = None):
        self.name = name
        self.script = script
        self.url = url
        self.transport = transport or settings.MCP_TRANSPORT
        self._session = None
        self._stack = None
        self.connected = False

    async def connect(self) -> bool:
        try:
            if self.transport == "sse" and self.url:
                from mcp.client.sse import sse_client
                self._stack = sse_client(self.url)
            else:
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client
                script_path = str(_boot.ROOT / "mcp_servers" / (self.script or ""))
                params = StdioServerParameters(command=sys.executable, args=[script_path])
                self._stack = stdio_client(params)

            # Enter the stack, then the session.
            entered = await self._stack.__aenter__()
            self._read, self._write = entered
            from mcp import ClientSession
            self._session = ClientSession(self._read, self._write)
            await self._session.__aenter__()
            await self._session.initialize()
            self.connected = True
            return True
        except Exception as exc:  # pragma: no cover - depends on runtime MCP
            self.connected = False
            await self.close()
            return False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if not self.connected or self._session is None:
            raise RuntimeError(f"MCP connection to {self.name} is not available")
        result = await self._session.call_tool(tool_name, arguments)
        return self._parse(result)

    @staticmethod
    def _parse(result: Any) -> Any:
        if not getattr(result, "content", None):
            return None
        # Concatenate text content blocks, then parse JSON.
        text = "\n".join(c.text for c in result.content if getattr(c, "text", None))
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    async def close(self) -> None:
        try:
            if self._session is not None:
                await self._session.__aexit__(None, None, None)
        except Exception:
            pass
        self._session = None
        try:
            if self._stack is not None:
                await self._stack.__aexit__(None, None, None)
        except Exception:
            pass
        self._stack = None
        self.connected = False


# ──────────────────────────────────────────────────────────────────────────────
# Mock data helpers
# ──────────────────────────────────────────────────────────────────────────────

_INCOME_CATEGORIES = {"SALARY", "FREELANCE", "INTEREST", "DIVIDEND"}


class MarketDataNotFound(Exception):
    """Raised when a market symbol is not recognised."""


def known_market_symbols() -> set:
    from mock_market_adapter import SYMBOL_BASE_PRICES
    return set(SYMBOL_BASE_PRICES.keys())


def validate_symbol(symbol: str) -> str:
    symbol = (symbol or "").strip().upper()
    if not symbol or symbol not in known_market_symbols():
        raise MarketDataNotFound(f"No market data for symbol: {symbol}")
    return symbol


def load_mock_data() -> Dict[str, Any]:
    with open(_boot.MOCK_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _active_month(transactions: List[Dict]) -> str:
    if not transactions:
        return "2026-08-01"
    latest = max(t["date"] for t in transactions)
    return latest[:7] + "-01"


def compute_monthly_baseline(data: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic monthly baseline (income + recurring EMI) from mock data."""
    transactions = data["transactions"]
    month_start = _active_month(transactions)
    month_end = month_start[:8] + "31"

    income = sum(
        t["amount"] for t in transactions
        if month_start <= t["date"] <= month_end
        and t["type"] == "CREDIT"
        and t.get("category") in _INCOME_CATEGORIES
    )

    emi_by_lender: Dict[str, float] = {}
    for t in transactions:
        if not (month_start <= t["date"] <= month_end):
            continue
        desc = t.get("description", "").upper()
        if t.get("category") == "LOAN_EMI" or "EMI" in desc or "LOAN" in desc:
            parts = t.get("description", "").split(" - ", 1)
            lender = parts[1].strip() if len(parts) > 1 else t.get("description", "UNKNOWN")
            emi_by_lender[lender] = t["amount"]

    existing_emi = round(sum(emi_by_lender.values()), 2)
    return {
        "month": month_start,
        "monthly_income": round(income, 2),
        "existing_emi": existing_emi,
        "emi_breakdown": emi_by_lender,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Services
# ──────────────────────────────────────────────────────────────────────────────

class Services:
    """Single object the tools use to read bank / market data deterministically."""

    def __init__(self, data_source: Optional[str] = None):
        self.data_source = (data_source or settings.DATA_SOURCE).lower()
        self._mock = load_mock_data()
        self._baseline = compute_monthly_baseline(self._mock)
        self._bank_mcp = MCPConn("bank", script=settings.BANK_MCP_SCRIPT)
        self._market_mcp = MCPConn("market", script=settings.MARKET_MCP_SCRIPT)
        self._bank_mode: str = "pending"
        self._market_mode: str = "pending"

    # ── lifecycle ──────────────────────────────────────────────────────────
    async def connect(self) -> Dict[str, str]:
        status = {"bank": "mock", "market": "mock", "loan": "engine"}
        if self.data_source != "mcp":
            self._bank_mode = "mock"
            self._market_mode = "mock"
            return status
        if await self._bank_mcp.connect():
            self._bank_mode = "mcp"
            status["bank"] = "mcp"
        else:
            self._bank_mode = "mock"
        if await self._market_mcp.connect():
            self._market_mode = "mcp"
            status["market"] = "mcp"
        else:
            self._market_mode = "mock"
        return status

    async def close(self) -> None:
        await self._bank_mcp.close()
        await self._market_mcp.close()

    @property
    def baseline(self) -> Dict[str, Any]:
        """Monthly baseline facts (income, recurring EMI)."""
        return dict(self._baseline)

    # ── bank helpers ───────────────────────────────────────────────────────
    async def get_accounts(self) -> List[Dict[str, Any]]:
        if self._bank_mode == "mcp":
            try:
                accounts = await self._bank_mcp.call_tool("get_accounts", {})
                if isinstance(accounts, list) and accounts:
                    return accounts
            except Exception:
                self._bank_mode = "mock"
        return self._mock["accounts"]

    async def get_transactions(self, account_id: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._bank_mode == "mcp":
            try:
                args = {}
                if account_id:
                    args["account_id"] = account_id
                if start_date:
                    args["start_date"] = start_date
                if end_date:
                    args["end_date"] = end_date
                txns = await self._bank_mcp.call_tool("get_transactions", args)
                if isinstance(txns, list):
                    return txns
            except Exception:
                self._bank_mode = "mock"
        txns = self._mock["transactions"]
        if account_id:
            txns = [t for t in txns if t["account_id"] == account_id]
        if start_date:
            txns = [t for t in txns if t["date"] >= start_date]
        if end_date:
            txns = [t for t in txns if t["date"] <= end_date]
        return txns

    async def get_loan_offers(self) -> List[Dict[str, Any]]:
        if self._bank_mode == "mcp":
            try:
                offers = await self._bank_mcp.call_tool("get_loan_offers", {})
                if isinstance(offers, list) and offers:
                    return offers
            except Exception:
                self._bank_mode = "mock"
        return self._mock["loan_offers"]

    # ── market helpers ─────────────────────────────────────────────────────
    async def get_price(self, symbol: str) -> float:
        from mock_market_adapter import MockMarketAdapter

        validate_symbol(symbol)
        if self._market_mode == "mcp":
            try:
                result = await self._market_mcp.call_tool("get_price", {"symbol": symbol})
                if isinstance(result, dict) and "price" in result:
                    return float(result["price"])
            except Exception:
                self._market_mode = "mock"
        adapter = MockMarketAdapter(seed=42)
        return adapter.get_latest_price(symbol)

    async def get_ohlc(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        from mock_market_adapter import MockMarketAdapter

        validate_symbol(symbol)
        if self._market_mode == "mcp":
            try:
                result = await self._market_mcp.call_tool("get_ohlc", {"symbol": symbol, "days": days})
                if isinstance(result, dict) and isinstance(result.get("bars"), list):
                    return result["bars"]
            except Exception:
                self._market_mode = "mock"
        adapter = MockMarketAdapter(seed=42)
        return adapter.get_ohlc_history(symbol, days)


# Module-level shared instance (assigned by the FastAPI lifespan).
services: Optional[Services] = None


def get_services() -> Services:
    """Return the process-wide Services instance (created on demand)."""
    global services
    if services is None:
        services = Services()
    return services

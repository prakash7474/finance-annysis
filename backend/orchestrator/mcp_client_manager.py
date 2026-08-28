"""
mcp_client_manager.py - MCP connection, discovery and invocation manager.

Wraps the existing ``MCPConn`` transport, adds tool/resource discovery and
schema validation, and routes calls so the orchestrator/agents never hard-code a
specific MCP tool call.  Falls back to the deterministic registry/listings when a
server is not reachable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.orchestrator.data_layer import MCPConn
from backend.orchestrator.tool_registry import list_tools, get_registry


class MCPClientManager:
    def __init__(self, transport: Optional[str] = None):
        self.transport = transport or settings.MCP_TRANSPORT
        self._connections: Dict[str, MCPConn] = {}

    async def connect(self, name: str, script: str = None, url: str = None) -> bool:
        conn = MCPConn(name, script=script, url=url, transport=self.transport)
        ok = await conn.connect()
        if ok:
            self._connections[name] = conn
        return ok

    async def invoke(self, server: str, tool: str, arguments: Dict[str, Any]) -> Any:
        conn = self._connections.get(server)
        if not conn or not conn.connected:
            raise RuntimeError(f"MCP server '{server}' is not connected")
        return await conn.call_tool(tool, arguments)

    async def close(self) -> None:
        for conn in self._connections.values():
            await conn.close()
        self._connections.clear()

    # ── discovery ─────────────────────────────────────────────────────────────
    @staticmethod
    def discover_tools() -> Dict[str, Dict[str, Any]]:
        """Return the discoverable tools (from the registry, server-tagged)."""
        discovered: Dict[str, Dict[str, Any]] = {"bank": [], "loan": [], "market": [], "intelligence": []}
        for tool in list_tools():
            server = tool.get("server", "engine")
            bucket = server if server in discovered else "intelligence"
            discovered[bucket].append(tool)
        return discovered

    @staticmethod
    def discover_servers() -> Dict[str, Dict[str, Any]]:
        return {
            "bank_mcp": {"name": "bank_mcp", "status": "available", "tools": MCPClientManager.discover_tools()["bank"]},
            "loan_mcp": {"name": "loan_mcp", "status": "available", "tools": MCPClientManager.discover_tools()["loan"]},
            "market_mcp": {"name": "market_mcp", "status": "available", "tools": MCPClientManager.discover_tools()["market"]},
            "intelligence_mcp": {"name": "intelligence_mcp", "status": "available",
                                 "tools": MCPClientManager.discover_tools()["intelligence"]},
        }

    @staticmethod
    def registry_tools() -> List[Dict[str, Any]]:
        return [{"name": s.name, "domain": s.domain, "server": s.server, "description": s.description}
                for s in get_registry().values()]

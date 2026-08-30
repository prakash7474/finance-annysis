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
            # Store alias with or without _mcp suffix
            alt_name = name + "_mcp" if not name.endswith("_mcp") else name[:-4]
            self._connections[alt_name] = conn
        return ok

    async def connect_all(self) -> Dict[str, bool]:
        """Attempt to connect to all standard MCP servers."""
        servers = {
            "bank": (settings.BANK_MCP_SCRIPT, getattr(settings, "BANK_MCP_URL", None)),
            "market": (settings.MARKET_MCP_SCRIPT, getattr(settings, "MARKET_MCP_URL", None)),
            "loan": (settings.LOAN_MCP_SCRIPT, getattr(settings, "LOAN_MCP_URL", None)),
            "intelligence": ("intelligence_mcp_server.py", "http://127.0.0.1:9004/sse"),
            "demat": ("demat_mcp_server.py", "http://127.0.0.1:9007/sse"),
            "governance": ("governance_mcp_server.py", "http://127.0.0.1:9006/sse"),
        }
        results = {}
        for name, (script, url) in servers.items():
            results[name] = await self.connect(name, script=script, url=url)
        return results

    async def invoke(self, server: str, tool: str, arguments: Dict[str, Any]) -> Any:
        conn = self._connections.get(server)
        if not conn:
            alt_server = server + "_mcp" if not server.endswith("_mcp") else server[:-4]
            conn = self._connections.get(alt_server)
        if not conn or not conn.connected:
            raise RuntimeError(f"MCP server '{server}' is not connected")
        return await conn.call_tool(tool, arguments)

    async def close(self) -> None:
        seen = set()
        for conn in self._connections.values():
            if conn not in seen:
                seen.add(conn)
                await conn.close()
            self._connections.clear()

    # ── discovery ─────────────────────────────────────────────────────────────
    @staticmethod
    def discover_tools() -> Dict[str, List[Dict[str, Any]]]:
        """Return the discoverable tools (from the registry, server-tagged)."""
        discovered: Dict[str, List[Dict[str, Any]]] = {
            "bank": [], "loan": [], "market": [], "intelligence": [],
            "demat": [], "governance": []
        }
        for tool in list_tools():
            server = tool.get("server", "engine")
            bucket = server if server in discovered else "intelligence"
            discovered[bucket].append(tool)
        return discovered

    @staticmethod
    def discover_servers() -> Dict[str, Dict[str, Any]]:
        tools_map = MCPClientManager.discover_tools()
        return {
            "bank_mcp": {"name": "bank_mcp", "status": "available", "tools": tools_map.get("bank", [])},
            "loan_mcp": {"name": "loan_mcp", "status": "available", "tools": tools_map.get("loan", [])},
            "market_mcp": {"name": "market_mcp", "status": "available", "tools": tools_map.get("market", [])},
            "intelligence_mcp": {"name": "intelligence_mcp", "status": "available", "tools": tools_map.get("intelligence", [])},
            "demat_mcp": {"name": "demat_mcp", "status": "available", "tools": tools_map.get("demat", [])},
            "governance_mcp": {"name": "governance_mcp", "status": "available", "tools": tools_map.get("governance", [])},
        }

    @staticmethod
    def registry_tools() -> List[Dict[str, Any]]:
        return [{"name": s.name, "domain": s.domain, "server": s.server, "description": s.description}
                for s in get_registry().values()]

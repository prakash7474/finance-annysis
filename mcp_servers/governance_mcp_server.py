"""
governance_mcp_server.py - Phase 2 Governance MCP (mocked accounts).

Exposes read-only account snapshots (paper) and the risk-profile the Rules Engine
uses.  Unknown accounts return a structured ACCOUNT_NOT_LINKED error.

Hardened: input validation, structured error responses, health check.
"""

import json
import time

from mcp.server.mcpserver import MCPServer

try:
    from _common import run_server
except ImportError:
    from mcp_servers._common import run_server
from accounts_provider import AccountNotLinked, provider
from structured_logger import get_logger, metrics

log = get_logger("governance_mcp")

mcp = MCPServer("governance-accounts", instructions="Mocked account snapshots (paper)")
_start_time = time.time()

VALID_ACCOUNT_IDS = {"ACC_CONSERVATIVE", "ACC_MODERATE", "ACC_AGGRESSIVE"}


def _validate_account_id(account_id: str) -> str | None:
    """Return error JSON string if invalid, else None."""
    if not account_id or not isinstance(account_id, str):
        return json.dumps({"error": "VALIDATION_ERROR", "message": "account_id is required"})
    return None


@mcp.resource("governance://accounts/{account_id}/snapshot")
def resource_snapshot(account_id: str) -> str:
    err = _validate_account_id(account_id)
    if err:
        metrics.increment("governance_validation_error")
        return err
    try:
        snapshot = provider.get_snapshot(account_id)
        metrics.increment("governance_snapshot_fetched")
        return json.dumps(snapshot.model_dump())
    except AccountNotLinked as exc:
        metrics.increment("governance_account_not_linked")
        log.warning("account_not_linked", account_id=account_id)
        return json.dumps({"error": exc.error_code, "message": exc.message})
    except Exception as exc:
        metrics.increment("governance_internal_error")
        log.exception("snapshot_error", account_id=account_id)
        return json.dumps({"error": "INTERNAL_ERROR", "message": "Failed to fetch snapshot."})


@mcp.tool()
def get_account_snapshot(account_id: str) -> str:
    """Fetch a mocked account snapshot by id."""
    return resource_snapshot(account_id)


@mcp.tool()
def list_accounts() -> str:
    """List available mocked accounts."""
    metrics.increment("governance_list_accounts")
    return json.dumps({"accounts": [s.model_dump() for s in provider.list_snapshots()]})


@mcp.tool()
def health_check() -> str:
    """Health check: returns server uptime and status."""
    return json.dumps({
        "status": "healthy",
        "server": "governance-accounts",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "accounts": list(VALID_ACCOUNT_IDS),
        "metrics": metrics.snapshot(),
    })


if __name__ == "__main__":
    run_server(mcp, default_port=9006)

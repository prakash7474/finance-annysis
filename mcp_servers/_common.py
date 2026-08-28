"""Shared bootstrap for the standalone MCP servers.

Ensures the repo root is importable and runs the MCP server over stdio
(default) or SSE (``--sse --port N``) so it can be launched in a terminal or
auto-spawned by the backend.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def run_server(mcp, default_port: int = 9000) -> None:
    if "--sse" in sys.argv:
        port = default_port
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])
        import uvicorn

        app = mcp.sse_app()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    else:
        mcp.run()

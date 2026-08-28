"""Phase 6 routes: agent status, multi-agent routing, tool discovery, voice WS."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.api.deps import error_response, get_state
from backend.orchestrator.mcp_client_manager import MCPClientManager
from backend.schemas.common import StandardErrorCode
from backend.voice.session_manager import VoiceSessionManager

router = APIRouter(tags=["phase6"])
voice_manager = VoiceSessionManager()


class AgentRouteRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: Optional[str] = None


@router.get("/api/agents")
async def agents():
    st = get_state()
    if st.multi_agent is None:
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Multi-agent orchestrator not initialized.", status_code=503)
    return {"agents": st.multi_agent.agent_status()}


@router.get("/api/tools")
async def tools():
    return {"discovery": MCPClientManager.discover_tools(),
            "servers": MCPClientManager.discover_servers()}


@router.post("/api/agents/route")
async def agent_route(req: AgentRouteRequest):
    st = get_state()
    if st.multi_agent is None:
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Multi-agent orchestrator not initialized.", status_code=503)
    try:
        response = await st.multi_agent.route(req.message, session_id=req.session_id)
        return response
    except Exception as exc:  # noqa: BLE001 - never leak a traceback
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Multi-agent routing failed.", status_code=500)


@router.get("/api/audit/{trace_id}")
async def audit(trace_id: str):
    from audit_logger import get_audit

    entries = get_audit(trace_id)
    if not entries:
        return error_response(StandardErrorCode.INTERNAL_ERROR, f"No audit trail for {trace_id}.",
                              trace_id=trace_id, status_code=404)
    return {"trace_id": trace_id, "audit": entries}


@router.websocket("/api/voice")
async def voice_ws(ws: WebSocket):
    await ws.accept()
    session = voice_manager.create()
    await ws.send_text(json.dumps({"type": "started", "session_id": session.session_id, "mode": session.mode}))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"type": "audio", "data": raw}

            mtype = data.get("type", "audio")
            if mtype == "stop":
                await ws.send_text(json.dumps({"type": "stopped", "session_id": session.session_id}))
                break
            if mtype == "interrupt":
                result = session.interrupt()
                await ws.send_text(json.dumps({"type": "interrupted", **result}))
                continue

            utterance = data.get("data") or data.get("text") or ""
            if not utterance:
                continue
            await ws.send_text(json.dumps({"type": "transcript", "utterance": utterance}))
            try:
                response = await session.process(utterance)
            except asyncio.CancelledError:
                await ws.send_text(json.dumps({"type": "interrupted"}))
                continue
            reply = response.get("message", "")
            async for chunk in session.stream_reply(reply):
                await ws.send_text(json.dumps({"type": "reply", "chunk": chunk}))
                if chunk == "[interrupted]":
                    break
            await ws.send_text(json.dumps({"type": "done", "trace_id": response.get("trace_id"),
                                           "facts": response.get("facts", {})}))
    except WebSocketDisconnect:
        pass
    finally:
        voice_manager.remove(session.session_id)

"""Unified chat API routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.deps import error_response, get_state
from backend.governance.tracing import new_id
from backend.orchestrator.tool_registry import list_tools
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.schemas.common import StandardErrorCode
from backend.state import state

router = APIRouter(tags=["chat"])


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    st = get_state()
    if st.orchestrator is None:
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Chat service is not initialized.",
                              status_code=503)
    try:
        response = await st.orchestrator.route(req.message, session_id=req.session_id)
        return response
    except Exception as exc:  # noqa: BLE001 - never leak stack traces
        trace_id = new_id("trace")
        return error_response(StandardErrorCode.INTERNAL_ERROR, "Chat processing failed.",
                              trace_id=trace_id, status_code=500)


@router.get("/api/chat/tools")
async def chat_tools():
    return {"tools": list_tools()}

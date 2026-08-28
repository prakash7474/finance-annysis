"""
voice_routes.py - Voice service abstraction.

The orchestrator is never coupled to voice: ``VoiceService`` wraps a
``start_session / send_audio / receive_audio / interrupt / stop_session``
interface.  If the Gemini Live (realtime) API is configured it can be plugged in
without touching the orchestrator; otherwise a deterministic text fallback keeps
everything functioning.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from backend.api.deps import error_response, get_state
from backend.governance.tracing import new_id
from backend.schemas.common import StandardErrorCode

router = APIRouter(prefix="/api/voice", tags=["voice"])


@dataclass
class VoiceSession:
    session_id: str
    transcript: List[Dict[str, str]] = field(default_factory=list)
    active: bool = False
    mode: str = "text-fallback"


class VoiceService:
    """Pluggable voice abstraction (Gemini Live ready)."""

    def start_session(self) -> VoiceSession:
        session = VoiceSession(session_id=new_id("voice"))
        session.active = True
        return session

    async def send_audio(self, session: VoiceSession, audio: str) -> Dict[str, Any]:
        """Handle a voice input chunk.

        In text-fallback mode ``audio`` may carry either base64-encoded audio
        (decoded to a placeholder transcript) or a literal text query.
        """
        text_query = self._translate_audio(audio)
        st = get_state()
        response = None
        if st.orchestrator is not None:
            chat_resp = await st.orchestrator.route(text_query, session_id=session.session_id)
            response = {"reply": chat_resp.message, "tools_used": chat_resp.tools_used,
                        "trace_id": chat_resp.trace_id}
        else:
            response = {"reply": "Voice service is not initialized.", "tools_used": [], "trace_id": None}
        session.transcript.append({"role": "user", "content": text_query})
        session.transcript.append({"role": "assistant", "content": response.get("reply", "")})
        return {"session_id": session.session_id, "transcript": text_query, **response}

    def receive_audio(self, session: VoiceSession) -> Dict[str, Any]:
        return {"session_id": session.session_id, "reply": session.transcript[-1]["content"]
                if session.transcript else ""}

    def interrupt(self, session: VoiceSession) -> Dict[str, Any]:
        return {"session_id": session.session_id, "interrupted": True}

    def stop_session(self, session: VoiceSession) -> Dict[str, Any]:
        session.active = False
        return {"session_id": session.session_id, "stopped": True}

    @staticmethod
    def _translate_audio(audio: str) -> str:
        """Best-effort decode: if it's base64/audio we can't transcribe offline,
        so fall back to a text query marker; if it's plain text, use it directly."""
        try:
            decoded = base64.b64decode(audio, validate=True)
            if decoded and all(32 <= b < 127 for b in decoded[:64]):
                return decoded.decode("utf-8", errors="ignore").strip() or "What is my financial status?"
        except Exception:
            pass
        return audio.strip() if audio and len(audio) < 1000 else "What is my financial status?"


_sessions: Dict[str, VoiceSession] = {}
_service = VoiceService()


@router.post("/start-session")
async def start_session():
    session = _service.start_session()
    _sessions[session.session_id] = session
    return {"session_id": session.session_id, "mode": session.mode}


@router.post("/send-audio")
async def send_audio(payload: Dict[str, Any]):
    session_id = payload.get("session_id")
    session = _sessions.get(session_id)
    if session is None:
        return error_response(StandardErrorCode.SESSION_ERROR, "Voice session not found.", status_code=404)
    result = await _service.send_audio(session, payload.get("audio") or payload.get("text") or "")
    return result


@router.get("/receive-audio")
async def receive_audio(session_id: str):
    session = _sessions.get(session_id)
    if session is None:
        return error_response(StandardErrorCode.SESSION_ERROR, "Voice session not found.", status_code=404)
    return _service.receive_audio(session)


@router.post("/interrupt")
async def interrupt(payload: Dict[str, Any]):
    session = _sessions.get(payload.get("session_id"))
    if session is None:
        return error_response(StandardErrorCode.SESSION_ERROR, "Voice session not found.", status_code=404)
    return _service.interrupt(session)


@router.post("/stop-session")
async def stop_session(payload: Dict[str, Any]):
    session_id = payload.get("session_id")
    session = _sessions.get(session_id)
    if session is None:
        return error_response(StandardErrorCode.SESSION_ERROR, "Voice session not found.", status_code=404)
    result = _service.stop_session(session)
    _sessions.pop(session_id, None)
    return result

"""voice/session_manager.py - in-memory VoiceSession store (swappable)."""

from __future__ import annotations

import uuid
from typing import Dict, Optional

from backend.voice.live_session import VoiceSession


class VoiceSessionManager:
    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}

    def create(self) -> VoiceSession:
        sid = f"voice_{uuid.uuid4().hex[:10]}"
        session = VoiceSession(session_id=sid)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Optional[VoiceSession]:
        return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def count(self) -> int:
        return len(self._sessions)

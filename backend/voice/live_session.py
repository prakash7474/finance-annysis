"""voice/live_session.py - real-time voice session with interruption."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class VoiceSession:
    session_id: str
    mode: str = "text-fallback"
    active: bool = True
    interrupted: bool = False
    context: Optional[Any] = None          # SessionContext / multi-agent backend
    transcript: List[Dict[str, str]] = field(default_factory=list)
    _current: Optional[asyncio.Task] = None

    def interrupt(self) -> Dict[str, Any]:
        """Stop the current generation and flag interruption."""
        self.interrupted = True
        if self._current and not self._current.done():
            self._current.cancel()
        return {"session_id": self.session_id, "interrupted": True}

    async def process(self, utterance: str) -> Dict[str, Any]:
        """Process a speech utterance through the orchestrator (voice respects
        the same governance/risk/approval path as text)."""
        # Determine the appropriate backend: multi-agent if available.
        from backend.state import state

        response = None
        if state.multi_agent is not None:
            response = await state.multi_agent.route(utterance, session_id=self.session_id)
        elif state.orchestrator is not None:
            response = await state.orchestrator.route(utterance, session_id=self.session_id)
        else:
            response = {"message": "Voice service is not initialized.", "trace_id": None}

        self.transcript.append({"role": "user", "content": utterance})
        self.transcript.append({"role": "assistant", "content": response.get("message", "")})
        self.interrupted = False
        return response

    async def stream_reply(self, text: str) -> AsyncIterator[str]:
        """Deterministic streamed reply (mock audio)."""
        step = 40
        for i in range(0, len(text), step):
            if self.interrupted:
                yield "[interrupted]"
                return
            chunk = text[i:i + step]
            yield chunk
            await asyncio.sleep(0.02)

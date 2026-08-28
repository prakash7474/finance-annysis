"""Tests for the Voice session (process, streaming, interruption)."""

import asyncio

from backend.voice.live_session import VoiceSession


def test_process_returns_reply():
    async def go():
        vs = VoiceSession("voice_1")
        resp = await vs.process("What is my financial health?")
        assert "message" in resp
        assert len(vs.transcript) == 2
    asyncio.run(go())


def test_stream_reply_yields_chunks():
    async def go():
        vs = VoiceSession("voice_2")
        chunks = []
        async for c in vs.stream_reply("This reply will be streamed in multiple small chunks of text."):
            chunks.append(c)
        assert len(chunks) >= 2
        assert "".join(chunks).startswith("This reply")
    asyncio.run(go())


def test_interrupt_stops_stream():
    async def go():
        vs = VoiceSession("voice_3")
        vs.interrupt()
        assert vs.interrupted is True
        chunks = []
        async for c in vs.stream_reply("A very long sentence that should be interrupted immediately."):
            chunks.append(c)
            if c == "[interrupted]":
                break
        assert chunks[-1] == "[interrupted]"
    asyncio.run(go())


def test_interrupt_returns_structured():
    vs = VoiceSession("voice_4")
    result = vs.interrupt()
    assert result["interrupted"] is True
    assert result["session_id"] == "voice_4"

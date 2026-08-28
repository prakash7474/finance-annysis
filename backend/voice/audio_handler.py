"""voice/audio_handler.py - audio <-> transcript adapter (mock for offline).

Gemini Live streaming is behind this interface; locally we provide a
deterministic mock that treats speech as text and synthesises a streamed reply.
"""

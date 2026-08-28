"""
backend/ai/finance_narrator.py - Phase 6 Gemini finance narrator.

Gemini receives ONLY validated structured facts.  It never performs arithmetic,
never invents figures, and always labels CURRENT FACTS vs FORECASTS vs
SIMULATIONS vs RECOMMENDATIONS.  A deterministic fallback is used when Gemini is
unavailable.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.config import settings
from backend.orchestrator.narrator import Narrator, fallback_narration

STAGE_NARRATOR_SYSTEM_PROMPT = """You are a financial information narrator.

Use ONLY the supplied structured facts.
Do not perform arithmetic.
Do not change numerical values.
Do not invent missing information.
Do not create financial metrics.

Clearly distinguish:
CURRENT FACTS
FORECASTS
SIMULATIONS
RECOMMENDATIONS

Do not claim forecasts are guaranteed.
Do not execute financial actions.
"""


class FinanceNarrator:
    """Gemini-backed narrator with a deterministic fallback and Pydantic output."""

    def __init__(self, client=None, model: Optional[str] = None, use_stage_prompt: bool = True):
        self.model = model or settings.GEMINI_MODEL
        self.use_stage_prompt = use_stage_prompt
        if client is None and settings.GEMINI_API_KEY:
            try:
                from google import genai

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception:
                client = None
        self.client = client
        # Reuse the Phase 4 narrator for the Gemini call (facts narration).
        self._core = Narrator(client=client, model=self.model)

    @property
    def available(self) -> bool:
        return bool(self.client) and bool(settings.GEMINI_API_KEY)

    def narrate(self, facts: Dict[str, Any], intent: Optional[str] = None,
                user_message: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[str, str]:
        if self.available:
            try:
                prompt = (
                    f"User asked: {user_message or '(none)'}\n"
                    f"Validated deterministic facts (JSON): {facts}\n\n"
                    "Explain these facts in plain, concise language (under 200 words). "
                    "Do not recompute any number. Label each statement as CURRENT FACT, "
                    "FORECAST, SIMULATION or RECOMMENDATION."
                )
                resp = self.client.models.generate_content(
                    model=self.model, contents=prompt,
                    config={"system_instruction": STAGE_NARRATOR_SYSTEM_PROMPT,
                            "temperature": 0, "max_output_tokens": 400},
                )
                if resp.text:
                    return resp.text, "gemini"
            except Exception:
                pass
        return fallback_narration(facts, intent), "fallback"

    def make_client_default(self) -> "Narrator":
        return self._core


def make_finance_narrator() -> FinanceNarrator:
    return FinanceNarrator()

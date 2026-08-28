"""Pytest configuration for FinPilot.

Ensures the project root is importable and forces deterministic, offline test
behaviour (mock data source + fallback narrator - no network, no Gemini).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force deterministic, offline behaviour for ALL tests:
#  - mock data source (no MCP subprocesses)
#  - empty Gemini key -> narrator always falls back to deterministic summary
os.environ.setdefault("DATA_SOURCE", "mock")
os.environ["GEMINI_API_KEY"] = ""
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("ENABLE_SSE_EVENTS", "false")

"""Path bootstrap for the FinPilot backend.

Ensures the project root is importable so engines, adapters and mock data at
the repository root can be imported from any backend module.
"""

import os
import sys
from pathlib import Path

# Repository root (parent of the ``backend`` package).
ROOT = Path(__file__).resolve().parents[1]
_STR_ROOT = str(ROOT)
if _STR_ROOT not in sys.path:
    sys.path.insert(0, _STR_ROOT)

# Convenience paths used throughout the backend.
DATA_DIR = ROOT / "data"
MOCK_DATA_FILE = ROOT / "mock_data.json"

__all__ = ["ROOT", "DATA_DIR", "MOCK_DATA_FILE"]

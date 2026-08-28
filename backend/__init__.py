"""FinPilot backend package."""

# Importing the package always bootstraps the import path and exposes shared
# constants (ROOT / DATA_DIR / MOCK_DATA_FILE).
from backend import _boot  # noqa: F401  (re-exported via backend._boot)

__all__ = ["_boot"]

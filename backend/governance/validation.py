"""
validation.py - Validate tool inputs and produced facts.

Used by the orchestrator before invoking a tool and before the facts are handed
to the narrator, so malformed data is rejected before it reaches the LLM.
"""

from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code  # VALIDATION_ERROR
        self.message = message
        super().__init__(message)


def ensure_positive_number(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError("VALIDATION_ERROR", f"{name} must be a number")
    if number <= 0:
        raise ValidationError("VALIDATION_ERROR", f"{name} must be positive")
    return number


def ensure_non_negative_number(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError("VALIDATION_ERROR", f"{name} must be a number")
    if number < 0:
        raise ValidationError("VALIDATION_ERROR", f"{name} must be non-negative")
    return number


def ensure_positive_int(value: Any, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError("VALIDATION_ERROR", f"{name} must be an integer")
    if number <= 0:
        raise ValidationError("VALIDATION_ERROR", f"{name} must be positive")
    return number


def ensure_symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper()
    if not symbol:
        raise ValidationError("VALIDATION_ERROR", "symbol is required")
    if len(symbol) > 20:
        raise ValidationError("VALIDATION_ERROR", "symbol is too long")
    return symbol


def validate_facts(facts: dict) -> dict:
    """Ensure facts is a plain serializable dict (no nested secrets)."""
    if not isinstance(facts, dict):
        raise ValidationError("VALIDATION_ERROR", "facts must be a dictionary")
    return facts

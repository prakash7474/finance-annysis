"""Governance: validation helper tests."""

import pytest

from backend.governance.validation import (
    ValidationError,
    ensure_positive_int,
    ensure_positive_number,
    ensure_symbol,
    validate_facts,
)


def test_ensure_positive_number():
    assert ensure_positive_number("500", "amount") == 500.0
    with pytest.raises(ValidationError):
        ensure_positive_number(-5, "amount")
    with pytest.raises(ValidationError):
        ensure_positive_number("abc", "amount")


def test_ensure_positive_int():
    assert ensure_positive_int(36, "tenure") == 36
    with pytest.raises(ValidationError):
        ensure_positive_int(0, "tenure")
    with pytest.raises(ValidationError):
        ensure_positive_int(-1, "tenure")


def test_ensure_symbol():
    assert ensure_symbol("reliance") == "RELIANCE"
    with pytest.raises(ValidationError):
        ensure_symbol("")
    with pytest.raises(ValidationError):
        ensure_symbol("a" * 30)


def test_validate_facts():
    assert validate_facts({"a": 1}) == {"a": 1}
    with pytest.raises(ValidationError):
        validate_facts([])


def test_validation_error_code():
    try:
        ensure_positive_number(-1, "x")
    except ValidationError as exc:
        assert exc.error_code == "VALIDATION_ERROR"

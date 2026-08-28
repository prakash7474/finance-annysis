"""Unit tests for tool registry discoverability and validation."""

import pytest

from backend.governance.validation import ValidationError
from backend.orchestrator.tool_registry import (
    get_registry,
    get_tool,
    list_tools,
    require_tool,
)


def test_registry_has_core_tools():
    registry = get_registry()
    for name in ("get_cash_position", "calculate_loan", "calculate_dti", "get_quote",
                 "get_trend", "compare_loan_offers", "calculate_health_score"):
        assert name in registry


def test_registry_domains():
    registry = get_registry()
    assert registry["get_cash_position"].domain == "finance"
    assert registry["calculate_loan"].domain == "loan"
    assert registry["get_quote"].domain == "market"


def test_registry_servers():
    registry = get_registry()
    assert registry["get_cash_position"].server == "bank"
    assert registry["get_quote"].server == "market"
    assert registry["calculate_loan"].server == "loan"


def test_require_tool_unknown_raises():
    with pytest.raises(ValidationError):
        require_tool("not_a_real_tool")


def test_get_tool_returns_spec():
    spec = get_tool("get_quote")
    assert spec is not None
    assert spec.name == "get_quote"


def test_list_tools_discoverable():
    tools = list_tools()
    names = [t["name"] for t in tools]
    assert len(tools) >= 15
    assert names == sorted(names)
    for t in tools:
        assert {"name", "domain", "server", "description"} <= set(t.keys())


def test_every_tool_has_executor():
    registry = get_registry()
    for name, spec in registry.items():
        assert callable(spec.executor), f"{name} missing executor"

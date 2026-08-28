"""Governance: tracing + audit tests."""

from backend.governance import tracing
from backend.governance.audit import AuditLog


def test_new_id_is_namespaced_and_unique():
    a = tracing.new_id("trace")
    b = tracing.new_id("trace")
    assert a.startswith("trace_")
    assert a != b


def test_request_trace_has_all_ids():
    trace = tracing.Tracer.start("session_x")
    assert trace.trace_id.startswith("trace_")
    assert trace.request_id.startswith("req_")
    assert trace.session_id == "session_x"


def test_trace_step_emits_structured_entry():
    trace = tracing.Tracer.start()
    entry = trace.step("BANK", "get_balance", "SUCCESS", duration_ms=12.0)
    assert entry["component"] == "BANK"
    assert entry["operation"] == "get_balance"
    assert entry["status"] == "SUCCESS"
    assert entry["trace_id"] == trace.trace_id


def test_audit_records_structured_log():
    entry = AuditLog.record("trace_ABC", "loan_engine", "calculate_emi", status="success", duration_ms=15.0)
    assert entry["component"] == "loan_engine"
    assert entry["operation"] == "calculate_emi"
    assert entry["duration_ms"] == 15.0
    # secrets must never appear in audit entries
    assert "api_key" not in entry and "password" not in entry


def test_trace_log_lines_are_retained():
    trace = tracing.Tracer.start()
    trace.step("LOAN", "calculate_emi", "SUCCESS", duration_ms=3.0)
    lines = tracing.get_recent_log_lines(limit=50)
    assert any(l["trace_id"] == trace.trace_id for l in lines)

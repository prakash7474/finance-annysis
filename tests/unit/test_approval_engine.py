"""Unit tests for the human approval engine."""

import pytest

from approval_engine import ApprovalEngine, ApprovalError
from models.recommendation_models import Recommendation


def _rec(rec_id="REC_1"):
    return Recommendation(recommendation_id=rec_id, priority=1, category="DEBT",
                          title="Avoid borrowing", reason_codes=["HIGH_DTI"],
                          supporting_facts={}, confidence=0.9, requires_approval=True)


def test_pending_to_approved():
    eng = ApprovalEngine()
    eng.submit(_rec("R1"))
    result = eng.approve("R1")
    assert result["status"] == "APPROVED"


def test_pending_to_rejected():
    eng = ApprovalEngine()
    eng.submit(_rec("R2"))
    result = eng.reject("R2")
    assert result["status"] == "REJECTED"


def test_approved_cannot_be_approved_twice():
    eng = ApprovalEngine()
    eng.submit(_rec("R3"))
    eng.approve("R3")
    with pytest.raises(ApprovalError) as exc:
        eng.approve("R3")
    assert exc.value.code == "INVALID_STATE"


def test_rejected_cannot_execute():
    eng = ApprovalEngine()
    eng.submit(_rec("R4"))
    eng.reject("R4")
    assert eng.can_execute("R4") is False
    with pytest.raises(ApprovalError) as exc:
        eng.execute("R4")
    assert exc.value.code == "NOT_APPROVED"


def test_approved_can_execute():
    eng = ApprovalEngine()
    eng.submit(_rec("R5"))
    eng.approve("R5")
    assert eng.can_execute("R5") is True
    assert eng.execute("R5")["executed"] is True


def test_expire_pending():
    eng = ApprovalEngine()
    eng.submit(_rec("R6"))
    eng.expire("R6")
    assert eng.get("R6")["status"] == "EXPIRED"


def test_unknown_recommendation():
    eng = ApprovalEngine()
    with pytest.raises(ApprovalError) as exc:
        eng.approve("DOES_NOT_EXIST")
    assert exc.value.code == "NOT_FOUND"


def test_rejected_cannot_be_approved():
    eng = ApprovalEngine()
    eng.submit(_rec("R7"))
    eng.reject("R7")
    with pytest.raises(ApprovalError):
        eng.approve("R7")

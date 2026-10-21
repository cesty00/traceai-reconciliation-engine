"""Isolated synthetic human validation tests; no database or application writes."""
import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).parents[1]/"prototypes/core_uat_03/human_document_link.py"
spec=importlib.util.spec_from_file_location("link",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def candidate():
    return {"case_id":"SYN-CASE","wme_document":"SYN-PV",
            "wms_documents":["SYN-A","SYN-B"],"evidence_scope":"SYN-ITEM"}
def decision(status="CONFIRMED"):
    return {"decision":status,"reviewer":"TEST","reviewed_at":"2026-10-21T10:00:00+03:00",
            "comment":"Synthetic evidence reviewed","supporting_documents":["SYN-SHEET"],
            "people_checked":[{"role":"counter","verification_reference":"SYN-PERSON-CHECK"}],
            "stock_scope_checked":"SYN-WH","evidence_verified":True}
def test_document_link_confirmation_does_not_authorize_economic_match():
    r=m.stage_document_link_decision(candidate(),decision())
    assert r["human_link_status"]=="DOCUMENT_LINK_CONFIRMED"
    assert r["proposed_event"]["economic_verdict"]=="REVIEW"
    assert r["proposed_event"]["automatic_match_allowed"] is False
    assert r["persistence_performed"] is False
def test_confirmation_requires_verified_evidence():
    d=decision();d["evidence_verified"]=False
    with pytest.raises(ValueError):m.stage_document_link_decision(candidate(),d)
def test_unverified_personnel_rejected():
    d=decision();d["people_checked"]=[{"role":"counter"}]
    with pytest.raises(ValueError):m.stage_document_link_decision(candidate(),d)
def test_insufficient_evidence_stays_pending():
    d=decision("INSUFFICIENT");d["evidence_verified"]=False
    assert m.stage_document_link_decision(candidate(),d)["human_link_status"]=="HUMAN_VALIDATION_PENDING"
def test_audit_previous_hash_proposed_without_mutating_history():
    first=m.stage_document_link_decision(candidate(),decision("INSUFFICIENT"))["proposed_event"]
    history=[first];original=first.copy()
    second=m.stage_document_link_decision(candidate(),decision(),history)["proposed_event"]
    assert second["previous_hash"]==first["entry_hash"]
    assert first==original and len(history)==1

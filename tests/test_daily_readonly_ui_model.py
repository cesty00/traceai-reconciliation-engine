from traceai_reconciliation.daily_ui.read_model import operator_view
import pytest

def payload():
    return {"schema_version":"1","case_id":"SYN","product_code":"SYN-P","product_name":"Synthetic",
      "unit":"kg","difference":-5.0,"cause":"SYN","cause_status":"REVIEW",
      "evidence_level":"B","rules":["INV-01"],"correction_target":"REVIEW",
      "operator_action":"Verify original","operator_status":"CONFIRMAT","residual":0.0,
      "evidence":["Synthetic evidence"],"blockers":[],"warnings":[],
      "wms_mutation_allowed":False,"wme_mutation_allowed":False}
def test_existing_schema_readonly():
    result=operator_view(payload())
    assert result["difference"]==-5
    assert result["documentary_validation"]=="NOT_AVAILABLE"
    assert result["reviewer_validation_enabled"] is False
    assert result["economic_match_authorized"] is False
def test_old_operator_status_not_human_approval():
    assert operator_view(payload())["operator_status"]=="CONFIRMAT"
    assert operator_view(payload())["documentary_validation"]=="NOT_AVAILABLE"
def test_refuse_unsafe_authority():
    p=payload();p["wme_mutation_allowed"]=True
    with pytest.raises(ValueError):operator_view(p)
def test_missing_fields_rejected():
    p=payload();p.pop("evidence")
    with pytest.raises(ValueError):operator_view(p)

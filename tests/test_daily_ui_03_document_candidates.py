from traceai_reconciliation.daily_ui.read_model import operator_view
import pytest
def base():
    return {"schema_version":"1","case_id":"SYN","product_code":"SYN","product_name":"Synthetic","unit":"kg","difference":-5.0,"cause":"review","cause_status":"REVIEW","evidence_level":"B","rules":[],"correction_target":"REVIEW","operator_action":"Check","operator_status":"REVIEW","residual":0.0,"evidence":[],"blockers":[],"warnings":[],"wms_mutation_allowed":False,"wme_mutation_allowed":False}
def test_legacy_output_unchanged():
    assert operator_view(base())["document_candidates"]==[]
def test_candidate_forced_unverified_even_if_input_claims_verified():
    p=base();p["document_candidates"]=[{"system":"WMS","document":"SYN-DOC","source_status":"VERIFIED","events":[{"quantity":-5.0,"lot":"L","source_status":"VERIFIED"}]}]
    v=operator_view(p)
    assert v["document_candidates"][0]["source_status"]=="UNVERIFIED"
    assert v["document_candidates"][0]["human_validation"]=="PENDING"
    assert v["document_candidates"][0]["events"][0]["source_status"]=="UNVERIFIED"
def test_malformed_candidate_fails():
    p=base();p["document_candidates"]=[{"system":"WMS","events":[]}]
    with pytest.raises(ValueError):operator_view(p)

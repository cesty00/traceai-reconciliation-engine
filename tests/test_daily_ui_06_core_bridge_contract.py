"""CORE-DAILY-UI-06: integration contract using real self-service JSON nesting.

Synthetic data only. PR #68 exact-head real-data replay remains separate.
"""
from traceai_reconciliation.daily_ui.inventory_candidates import inventory_document_candidates
from traceai_reconciliation.daily_ui.read_model import operator_view

def operator_payload():
    return {
        "schema_version":"1", "case_id":"SYN-UAT-06",
        "product_code":"SYN-ITEM","product_name":"Synthetic inventory item","unit":"kg",
        "difference":-86.35,"cause":"Inventory adjustments","cause_status":"REVIEW",
        "evidence_level":"A","rules":["INV-01"],"correction_target":"REVIEW",
        "operator_action":"Examine source documents","operator_status":"REVIEW",
        "residual":0.0,"evidence":["Aggregate INV-01"],"blockers":[],
        "warnings":[],"wms_mutation_allowed":False,"wme_mutation_allowed":False,
    }

def case_payload():
    return {"investigation":{"case_id":"SYN-UAT-06","details":{
        "inventory_adjustment_matching":{"residual_wms_adjustments":[
          {"reason":"INV-MIN","quantity":-132.0,"contributing_event_refs":[
              {"document":"00060","lot":"LOT-1","quantity":-131.75,"source_pointer_status":"UNVERIFIED"},
              {"document":"00060","lot":"LOT-2","quantity":-0.25,"source_pointer_status":"UNVERIFIED"}]},
          {"reason":"INV-PLS","quantity":45.65,"contributing_event_refs":[
              {"document":"00060","lot":"LOT-3","quantity":45.65,"source_pointer_status":"UNVERIFIED"}]}
        ]}}}}

def test_nested_core_case_to_operator_view():
    case=case_payload()
    operator=operator_payload()
    assert case["investigation"]["case_id"]==operator["case_id"]
    candidates=inventory_document_candidates(case)
    operator["document_candidates"]=candidates
    view=operator_view(operator)
    assert len(view["document_candidates"])==1
    document=view["document_candidates"][0]
    assert document["document"]=="00060"
    assert len(document["events"])==3
    assert round(sum(x["quantity"] for x in document["events"]),2)==-86.35
    assert document["source_status"]=="UNVERIFIED"
    assert document["human_validation"]=="PENDING"
    assert view["operator_status"]=="REVIEW"
    assert view["economic_match_authorized"] is False
    assert view["reviewer_validation_enabled"] is False

def test_mixed_unmatched_documents_not_exclusively_attributed():
    case=case_payload()
    case["investigation"]["details"]["inventory_adjustment_matching"]["residual_wms_adjustments"].append(
        {"reason":"INV-PLS","quantity":160.4,"contributing_event_refs":[
            {"document":"SYN-OLDER","lot":"LOT-4","quantity":160.4}]}
    )
    documents=inventory_document_candidates(case)
    assert {d["document"] for d in documents}=={"00060","SYN-OLDER"}
    assert all(e["source_status"]=="UNVERIFIED" for d in documents for e in d["events"])
    payload=operator_payload()
    payload["document_candidates"]=documents
    display=operator_view(payload)
    assert all(d["source_status"]=="UNVERIFIED" for d in display["document_candidates"])

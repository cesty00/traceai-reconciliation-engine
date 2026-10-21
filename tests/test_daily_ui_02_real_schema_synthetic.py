from traceai_reconciliation.daily_ui.read_model import operator_view
def test_real_case_shape_synthetic_no_source_provenance():
    d={"schema_version":"1.0","case_id":"SYN-CASE","product_code":"SYN-P",
    "product_name":"Synthetic","unit":"Kilogram","difference":-86.35,
    "cause":"Inventory residual","cause_status":"CONFIRMATA","evidence_level":"A",
    "rules":["INV-01"],"correction_target":"REVIEW","operator_action":"Check originals",
    "operator_status":"REVIEW","residual":0.0,
    "evidence":["INV-01: aggregated amount only"],"blockers":[],
    "warnings":["UNMATCHED_OPERATIONS_8"],
    "wms_mutation_allowed":False,"wme_mutation_allowed":False}
    view=operator_view(d)
    assert view["difference"]==-86.35
    assert view["source_line_status"]=="SOURCE_LINES_NOT_VERIFIED"
    assert view["documentary_validation"]=="NOT_AVAILABLE"
    assert not view["economic_match_authorized"]

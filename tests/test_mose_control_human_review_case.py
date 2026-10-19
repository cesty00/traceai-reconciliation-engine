from traceai_reconciliation.mose_control.human_review_case import f91655_review_case

def test_real_case_requires_operator_validation():
    case = f91655_review_case()
    assert case.engine_verdict == "REVIEW"
    assert case.operator_status == "AWAITING_DOCUMENT_CHECK"
    assert case.wme_source_rows == (71944, 72103)

def test_case_requires_original_invoice_before_fix():
    case = f91655_review_case().to_dict()
    assert "Factura fiscala originala" in case["required_documents"][0]
    assert "nu se marcheaza MATCH automat" in case["decision_rule"]

def test_human_status_is_independent_from_engine_verdict():
    case = f91655_review_case()
    assert case.engine_verdict != "MATCH"
    assert case.candidate_excess_outflow_kg == "10"

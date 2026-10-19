from traceai_reconciliation.mose_control.case_dossier import compose_mose_case

def invoice(row, warehouse):
    return dict(document="91655", date="2026-03-11", source_row=row, warehouse=warehouse,
                product_code="SKU", product_name="FILE CRAP CU PIELE",
                quantity=-10, operation_type="F", unit="KG")

def test_case_91655_retains_two_source_rows_and_review():
    result = compose_mose_case(case_id="MOSE-F91655", invoices_wme=[
        invoice(71944, "DEPOZIT PRINCIPAL"), invoice(72103, "MOSE")])
    assert result["status"] == "AWAITING_OPERATOR_DOCUMENT_CHECK"
    assert {r["source_row"] for r in result["wme_invoices_source_evidence"]} == {71944, 72103}
    assert result["verdict"] == "REVIEW"
    assert result["automatic_correction_allowed"] is False

def test_candidate_transfer_is_never_promoted_to_proven_match():
    result = compose_mose_case(case_id="MOSE-F91655", invoices_wme=[invoice(71944, "MOSE")],
        transfers_wms_candidates=[dict(document="TRANSFER_MOSE-202520832", quantity=-10)])
    assert result["nt_to_wms_link"] == "NOT_VERIFIED"
    assert result["wms_transfer_candidates_unverified"][0]["quantity"] == -10

def test_missing_original_invoice_row_blocks():
    bad = invoice(100, "MOSE")
    bad.pop("source_row")
    assert compose_mose_case(case_id="A", invoices_wme=[bad])["status"] == "BLOCKED_WITH_REASON"

def test_mixed_invoice_documents_block():
    other = invoice(72103, "MOSE")
    other["document"] = "99999"
    assert compose_mose_case(case_id="A", invoices_wme=[invoice(71944, "MOSE"), other])["reason"] == "MULTIPLE_INVOICE_DOCUMENTS"

def test_balance_does_not_claim_stock_validation():
    result = compose_mose_case(case_id="A", invoices_wme=[invoice(71944, "MOSE")],
        observed_wme_balances=[dict(warehouse="MOSE", product_code="SKU", balance=0, source_row=71944)])
    assert result["stock_validation"] == "NOT_VERIFIED"
    assert result["wme_observed_balances_unverified_scope"][0]["balance"] == 0

def test_missing_invoice_blocks():
    assert compose_mose_case(case_id="A", invoices_wme=[])["reason"] == "MISSING_CASE_OR_INVOICE"

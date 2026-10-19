from traceai_reconciliation.mose_control.generic_evidence_audit import audit_mose_document_evidence

def evidence():
    return {
        "status": "AWAITING_OPERATOR_DOCUMENT_CHECK", "case_id": "MOSE-A",
        "invoice_document": "987", "wme_invoices_source_evidence": [
            {"document": "987", "warehouse": "MOSE", "source_row": 40},
            {"document": "987", "warehouse": "DEPOZIT PRINCIPAL", "source_row": 41}],
        "wme_nt_candidates_unverified": [], "wms_transfer_candidates_unverified": [],
        "wms_delivery_candidates_unverified": [],
    }

def test_generic_audit_never_promotes_to_match():
    outcome = audit_mose_document_evidence(evidence())
    assert outcome["verdict"] == "REVIEW"
    assert outcome["automatic_correction_allowed"] is False
    assert outcome["checks"]["MULTI_WAREHOUSE_F_OUTFLOW"] == "SUSPECT_REVIEW"

def test_missing_candidates_are_not_claimed_absent():
    outcome = audit_mose_document_evidence(evidence())
    assert outcome["checks"]["NT_WME_CANDIDATES"] == "NO_CANDIDATES_IN_SCREEN"
    assert outcome["checks"]["WMS_CUSTOMER_DELIVERY_CANDIDATES"] == "NO_SAME_CUSTOMER_CANDIDATE_IN_SCREEN"

def test_invalid_invoice_provenance_blocks():
    item = evidence()
    del item["wme_invoices_source_evidence"][0]["source_row"]
    assert audit_mose_document_evidence(item)["status"] == "SOURCE_PROVENANCE_INCOMPLETE_REVIEW"

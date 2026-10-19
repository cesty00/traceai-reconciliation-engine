from traceai_reconciliation.mose_control.reference_acceptance import audit_f91655_dossier

def dossier():
    return {
        "status": "AWAITING_OPERATOR_DOCUMENT_CHECK",
        "wme_invoices_source_evidence": [
            {"source_row": 71944, "warehouse": "DEPOZIT PRINCIPAL"},
            {"source_row": 72103, "warehouse": "MOSE"}],
        "wme_nt_candidates_unverified": [
            {"source_row": 71943}, {"source_row": 72102}],
        "wms_transfer_candidates_unverified": [
            {"document": "TRANSFER_MOSE-202520832"}],
    }

def test_f91655_reference_contract_is_read_only_review():
    r = audit_f91655_dossier(dossier())
    assert r["status"] == "REFERENCE_EVIDENCE_PRESENT_REVIEW"
    assert r["verdict"] == "REVIEW"
    assert r["automatic_correction_allowed"] is False

def test_missing_nt_does_not_pass_reference_audit():
    d = dossier()
    d["wme_nt_candidates_unverified"].pop()
    assert audit_f91655_dossier(d)["status"] == "REFERENCE_EVIDENCE_INCOMPLETE_REVIEW"

def test_wrong_warehouse_does_not_pass_reference_audit():
    d = dossier()
    d["wme_invoices_source_evidence"][1]["warehouse"] = "DEPOZIT PRINCIPAL"
    assert audit_f91655_dossier(d)["status"] == "REFERENCE_EVIDENCE_INCOMPLETE_REVIEW"

def test_missing_wms_transfer_remains_review():
    d = dossier()
    d["wms_transfer_candidates_unverified"] = []
    result = audit_f91655_dossier(d)
    assert result["status"] == "REFERENCE_EVIDENCE_INCOMPLETE_REVIEW"
    assert "WMS_TRANSFER_MOSE_REFERENCE" in result["missing"]
    assert result["verdict"] == "REVIEW"
    assert result["automatic_correction_allowed"] is False

def test_missing_both_nt_legs_and_transfer_reports_all():
    d = dossier()
    d["wme_nt_candidates_unverified"] = []
    d["wms_transfer_candidates_unverified"] = []
    result = audit_f91655_dossier(d)
    assert "WME_NT62513_TWO_LEGS" in result["missing"]
    assert "WMS_TRANSFER_MOSE_REFERENCE" in result["missing"]
    assert result["verdict"] == "REVIEW"

def test_non_open_case_blocks_reference_acceptance():
    d = dossier()
    d["status"] = "MATCH"
    assert audit_f91655_dossier(d)["status"] == "BLOCKED_NOT_AN_OPEN_REVIEW_CASE"

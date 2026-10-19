"""Acceptance audit against human-reviewed reference evidence for F91655.

This checks a generated dossier's source traceability, not fiscal correctness.
"""
from __future__ import annotations
from typing import Any, Mapping


def audit_f91655_dossier(dossier: Mapping[str, Any]) -> dict[str, Any]:
    if dossier.get("status") != "AWAITING_OPERATOR_DOCUMENT_CHECK":
        return {"status": "BLOCKED_NOT_AN_OPEN_REVIEW_CASE", "verdict": "REVIEW"}
    invoices = dossier.get("wme_invoices_source_evidence") or []
    got = {(int(r.get("source_row", -1)), str(r.get("warehouse", "")).upper())
           for r in invoices if isinstance(r, dict)}
    expected = {(71944, "DEPOZIT PRINCIPAL"), (72103, "MOSE")}
    nt = dossier.get("wme_nt_candidates_unverified") or []
    nt_rows = {int(r.get("source_row", -1)) for r in nt if isinstance(r, dict)}
    transfers = dossier.get("wms_transfer_candidates_unverified") or []
    transfer_docs = {str(r.get("document", "")) for r in transfers if isinstance(r, dict)}
    missing = []
    if got != expected:
        missing.append("WME_F91655_SOURCE_ROW_WAREHOUSE")
    if not {71943, 72102}.issubset(nt_rows):
        missing.append("WME_NT62513_TWO_LEGS")
    if "TRANSFER_MOSE-202520832" not in transfer_docs:
        missing.append("WMS_TRANSFER_MOSE_REFERENCE")
    return {
        "status": "REFERENCE_EVIDENCE_PRESENT_REVIEW" if not missing else "REFERENCE_EVIDENCE_INCOMPLETE_REVIEW",
        "missing": missing,
        "verdict": "REVIEW",
        "automatic_correction_allowed": False,
        "operator_action": "CHECK_ORIGINAL_INVOICE_AND_DELIVERY_DOCUMENTS",
        "notice": "Presence of references is not proof of WMS/WME match or accounting error.",
    }

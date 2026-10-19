"""Generic evidence completeness for MOSE F/NT/WMS review dossiers.

Reports source-backed candidates and gaps; never asserts a document match.
"""
from __future__ import annotations
from typing import Any, Mapping


def audit_mose_document_evidence(dossier: Mapping[str, Any]) -> dict[str, Any]:
    if dossier.get("status") != "AWAITING_OPERATOR_DOCUMENT_CHECK":
        return {"status": "BLOCKED_NOT_OPEN_REVIEW", "verdict": "REVIEW"}
    invoice = dossier.get("wme_invoices_source_evidence") or []
    if not invoice or any(
        not isinstance(row, dict)
        or not isinstance(row.get("source_row"), int)
        or not str(row.get("document") or "").strip()
        or not str(row.get("warehouse") or "").strip()
        for row in invoice
    ):
        return {"status": "SOURCE_PROVENANCE_INCOMPLETE_REVIEW", "verdict": "REVIEW"}
    nt = dossier.get("wme_nt_candidates_unverified") or []
    transfers = dossier.get("wms_transfer_candidates_unverified") or []
    deliveries = dossier.get("wms_delivery_candidates_unverified") or []
    warehouses = sorted({str(row["warehouse"]).upper() for row in invoice})
    checks = {
        "INVOICE_WME_SOURCE": "PRESENT",
        "MULTI_WAREHOUSE_F_OUTFLOW": "SUSPECT_REVIEW" if len(warehouses) > 1 else "NOT_INDICATED",
        "NT_WME_CANDIDATES": "PRESENT_UNVERIFIED" if nt else "NO_CANDIDATES_IN_SCREEN",
        "WMS_MOSE_TRANSFER_CANDIDATES": "PRESENT_UNVERIFIED" if transfers else "NO_CANDIDATES_IN_SCREEN",
        "WMS_CUSTOMER_DELIVERY_CANDIDATES": (
            "PRESENT_UNVERIFIED" if any(x.get("partner_screen") == "PARTNER_CANDIDATE" for x in deliveries)
            else "NO_SAME_CUSTOMER_CANDIDATE_IN_SCREEN"
        ),
        "WME_STOCK_ARITHMETIC": dossier.get("invoice_balance_evidence", {}).get(
            "status", "NOT_VERIFIED"
        ),
    }
    return {
        "status": "EVIDENCE_SCREEN_COMPLETE_REVIEW",
        "verdict": "REVIEW",
        "case_id": dossier.get("case_id"),
        "invoice_document": dossier.get("invoice_document"),
        "checks": checks,
        "automatic_correction_allowed": False,
        "operator_status": "AWAITING_DOCUMENT_CHECK",
        "note": "No candidate list is proof of a document MATCH. Empty or truncated screens cannot prove absence.",
    }

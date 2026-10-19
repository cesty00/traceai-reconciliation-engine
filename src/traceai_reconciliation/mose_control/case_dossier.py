"""Compose one MOSE investigation without promoting candidates into evidence.

Input records must already be sourced and normalized. This module is read-only.
It never computes a physical count or infers missing WME balances.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence


def _source(row: Mapping[str, Any], system: str) -> dict[str, Any]:
    fields = ("document", "date", "warehouse", "product_code", "product_name",
              "quantity", "source_row", "operation_type", "unit", "partner")
    result = {name: row.get(name) for name in fields if name in row}
    result["system"] = system
    return result


def compose_mose_case(
    *,
    case_id: str,
    invoices_wme: Sequence[Mapping[str, Any]],
    nt_wme_candidates: Sequence[Mapping[str, Any]] = (),
    delivery_wms_candidates: Sequence[Mapping[str, Any]] = (),
    transfers_wms_candidates: Sequence[Mapping[str, Any]] = (),
    observed_wme_balances: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Produce a full, conservative case. A row without source provenance blocks proof."""
    if not case_id or not invoices_wme:
        return {"status": "BLOCKED_WITH_REASON", "reason": "MISSING_CASE_OR_INVOICE", "verdict": "REVIEW"}
    missing = [i for i, row in enumerate(invoices_wme)
               if not isinstance(row.get("source_row"), int) or isinstance(row.get("source_row"), bool)
               or not str(row.get("document") or "").strip()
               or not str(row.get("warehouse") or "").strip()]
    if missing:
        return {"status": "BLOCKED_WITH_REASON", "reason": "MISSING_WME_PROVENANCE",
                "invalid_indices": missing, "verdict": "REVIEW"}
    invoice_docs = {str(row["document"]).strip() for row in invoices_wme}
    if len(invoice_docs) != 1:
        return {"status": "BLOCKED_WITH_REASON", "reason": "MULTIPLE_INVOICE_DOCUMENTS",
                "verdict": "REVIEW"}
    original_rows = [row["source_row"] for row in invoices_wme]
    if len(original_rows) != len(set(original_rows)):
        return {"status": "BLOCKED_WITH_REASON", "reason": "DUPLICATE_INVOICE_SOURCE_ROW",
                "verdict": "REVIEW"}
    balances = []
    for row in observed_wme_balances:
        if not all(k in row for k in ("warehouse", "product_code", "balance", "source_row")):
            continue
        balances.append(dict(row))
    return {
        "status": "AWAITING_OPERATOR_DOCUMENT_CHECK",
        "verdict": "REVIEW",
        "case_id": case_id,
        "invoice_document": next(iter(invoice_docs)),
        "wme_invoices_source_evidence": [_source(row, "WME") for row in invoices_wme],
        "wme_nt_candidates_unverified": [_source(row, "WME") for row in nt_wme_candidates],
        "wms_delivery_candidates_unverified": [_source(row, "WMS") for row in delivery_wms_candidates],
        "wms_transfer_candidates_unverified": [_source(row, "WMS") for row in transfers_wms_candidates],
        "wme_observed_balances_unverified_scope": balances,
        "stock_validation": "NOT_VERIFIED",
        "nt_to_wms_link": "NOT_VERIFIED",
        "invoice_to_delivery_link": "NOT_VERIFIED",
        "operator_status": "AWAITING_DOCUMENT_CHECK",
        "automatic_correction_allowed": False,
        "required_checks": [
            "Verify original fiscal invoice and actual quantity billed",
            "Verify all WME F rows and involved warehouses",
            "Verify NT legs and document-level WMS transfer correspondence",
            "Verify direct WMS customer deliveries separately from transfers",
            "Rebuild after-invoice WME balance per article and warehouse",
            "Record human conclusion and original documentary references",
        ],
    }

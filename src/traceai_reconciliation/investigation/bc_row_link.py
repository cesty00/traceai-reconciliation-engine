"""Strict documentary link between one WMS production consumption and WME BC.

This only proves source-row identity and quantities, never stock correction,
operator fault, or automated human approval.
"""
from __future__ import annotations

import re
from typing import Any

from .production_matching import normalize_document


def link_bc_rows(
    *,
    article_code: str,
    bc_document: str,
    wme_item_id: str,
    wms_rows: list[dict[str, Any]],
    wme_rows: list[dict[str, Any]],
    source_manifest: dict[str, dict[str, str]],
) -> dict[str, Any]:
    doc = normalize_document(bc_document)
    if not doc or not article_code or not wme_item_id:
        raise ValueError("BC link requires article code, document and verified WME item mapping")
    if not set(("wms", "wme")).issubset(source_manifest):
        raise ValueError("BC link missing both source identities")
    for system in ("wms", "wme"):
        meta = source_manifest[system]
        digest = meta.get("sha256", "")
        if not meta.get("file_name") or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError(f"BC link invalid {system} source hash")
    def location(row: dict[str, Any]) -> int:
        n = row.get("SourceRowNumber")
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError("BC link missing physical source coordinate")
        return n
    candidates_wms = [
        row for row in wms_rows
        if str(row.get("Cod articol", "")).strip() == article_code
        and normalize_document(row.get("Numar comanda")) == doc
        and str(row.get("Tip operatiune", "")).strip().casefold() == "ajustare negativa"
        and str(row.get("Cod-motiv", "")).strip().upper() == "PRODUCTION-IN"
    ]
    candidates_wme = [
        row for row in wme_rows
        if str(row.get("OperationType", "")).strip().upper() == "BC"
        and normalize_document(row.get("Document")) == doc
        and str(row.get("WMEItemId", "")).strip() == wme_item_id
    ]
    if len(candidates_wms) != 1 or len(candidates_wme) != 1:
        raise ValueError("BC link ambiguous or missing source event")
    wms, wme = candidates_wms[0], candidates_wme[0]
    wms_row, wme_row = location(wms), location(wme)
    try:
        wms_qty = float(wms["Cantitate"])
        wme_qty = float(wme["SignedQuantity"])
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("BC link missing numerical quantities") from exc
    if wms_qty >= 0 or wme_qty >= 0:
        raise ValueError("BC link expects negative consumption in both systems")
    return {
        "article_code": article_code, "bc_document": doc,
        "wme_item_id": wme_item_id,
        "wms_row": wms_row, "wme_row": wme_row,
        "wms_sha256": source_manifest["wms"]["sha256"],
        "wme_sha256": source_manifest["wme"]["sha256"],
        "wms_file": source_manifest["wms"]["file_name"],
        "wme_file": source_manifest["wme"]["file_name"],
        "wms_qty": wms_qty, "wme_qty": wme_qty,
        "difference": wms_qty - wme_qty,
        "status": "QTY_DIFF" if abs(wms_qty - wme_qty) > 0.001 else "QTY_EQUAL",
        "human_validation": "NOT_ATTACHED",
        "economic_match": False,
    }

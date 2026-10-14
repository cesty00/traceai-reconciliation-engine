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


def append_verified_bc_link(report: Any, link: dict[str, Any]) -> Any:
    """Attach a previously checked BC documentary link to a CaseReport.

    Fail closed on case/article mismatch and never change the stock verdict,
    economic interpretation or human-validation status.
    """
    if str(report.product_code).strip() != str(link.get("article_code", "")).strip():
        raise ValueError("BC link belongs to another product")
    if link.get("status") != "QTY_DIFF" or link.get("human_validation") != "NOT_ATTACHED":
        raise ValueError("BC link has unexpected status or human validation")
    if link.get("economic_match") is not False:
        raise ValueError("BC documentary link must not certify economic MATCH")
    document = normalize_document(link.get("bc_document"))
    if not document:
        raise ValueError("BC link document missing")
    import math
    for key in ("wms_qty", "wme_qty", "difference"):
        if not math.isfinite(float(link[key])):
            raise ValueError("BC link nonfinite quantity")
    if abs(float(link["wms_qty"]) - float(link["wme_qty"]) - float(link["difference"])) > 0.001:
        raise ValueError("BC link arithmetic mismatch")
    for system in ("wms", "wme"):
        n = link.get(system + "_row")
        digest = link.get(system + "_sha256", "")
        name = link.get(system + "_file", "")
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError("BC link lacks source row")
        if not name or not isinstance(digest, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            raise ValueError("BC link lacks valid source identity")

    # Deduplicate by (document, article); a different existing entry is
    # ambiguous and must be investigated rather than silently overwritten.
    key = f"BC={document} ARTICLE={link['article_code']}"
    existing = [
        item for item in report.conclusion_traceability
        if item.get("step") == "BC_VERIFIED_SOURCE_LINK" and item.get("key") == key
    ]
    if existing:
        raise ValueError("BC link already attached; manual review required")
    report.conclusion_traceability.append({
        "step": "BC_VERIFIED_SOURCE_LINK",
        "source": (
            f"WMS {link['wms_file']} / WME {link['wme_file']}"
        ),
        "key": key,
        "rule": "EXACT_BC_DOCUMENT_ARTICLE_SOURCE_ROW",
        "result": (
            f"WMS_ROW={link['wms_row']} SHA256={link['wms_sha256']} "
            f"WMS={link['wms_qty']:.3f}; "
            f"WME_ROW={link['wme_row']} SHA256={link['wme_sha256']} "
            f"WME={link['wme_qty']:.3f}; "
            f"DIFF={link['difference']:.3f}; "
            "HUMAN_VALIDATION_NOT_ATTACHED; NOT_ECONOMIC_MATCH"
        ),
        "evidence_level": "D",
    })
    return report

"""Conservative COR STOC <-> PV documentary candidate discovery.

This detector does not certify economic MATCH or remove residual stock effects.
It deliberately requires an explicit document reference and reports REVIEW only.
"""
from __future__ import annotations

import re
from typing import Any


def _document(value: object) -> str:
    match = re.search(r"(?<!\d)(\d{3,})(?!\d)", str(value or ""))
    return match.group(1) if match else ""


def find_cor_stoc_pv_candidates(
    wms_rows: list[dict[str, Any]],
    wme_rows: list[dict[str, Any]],
    *,
    tolerance: float = 0.001,
) -> list[dict[str, Any]]:
    """Return documentary review candidates, never reconciled/matched rows.

    Input rows must be scoped to a single verified article by the caller.
    Missing article scope is an integration blocker, not permission to match.
    The source row numbers are not inferred.
    """
    if tolerance < 0:
        raise ValueError("Negative tolerance")
    pv_by_doc: dict[str, list[dict[str, Any]]] = {}
    for row in wme_rows:
        if str(row.get("OperationType", "")).strip().upper() != "PV":
            continue
        doc = _document(row.get("Document"))
        if doc:
            pv_by_doc.setdefault(doc, []).append(row)

    result: list[dict[str, Any]] = []
    for doc, pv_rows in sorted(pv_by_doc.items()):
        referenced = [
            row for row in wms_rows
            if str(row.get("Cod-motiv", "")).strip().upper() == "COR STOC"
            and re.search(r"(?<!\d)" + re.escape(doc) + r"(?!\d)", str(row.get("Detalii", "")))
        ]
        if not referenced:
            continue
        days = {str(r.get("Data", "")).strip().split(" ")[0] for r in referenced}
        # No guessed day/warehouse equivalence; only evidence-based candidates.
        try:
            pv_total = sum(float(row["SignedQuantity"]) for row in pv_rows)
            referenced_total = sum(float(row["Cantitate"]) for row in referenced)
        except (ValueError, TypeError, KeyError):
            continue
        result.append({
            "pv_document": doc,
            "pv_quantity": round(pv_total, 6),
            "explicit_wms_quantity": round(referenced_total, 6),
            "quantity_equal_explicit_rows": abs(pv_total - referenced_total) <= tolerance,
            "wms_source_rows": [row.get("SourceRowNumber") for row in referenced],
            "wme_source_rows": [row.get("SourceRowNumber") for row in pv_rows],
            "status": "COR_STOC_PV_SOURCE_REVIEW",
            "economic_match": False,
            "stock_effect_verified": False,
            "human_validation": "NOT_ATTACHED",
        })
    return result

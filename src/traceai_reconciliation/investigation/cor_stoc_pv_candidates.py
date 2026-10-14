"""Conservative COR STOC <-> PV documentary candidate discovery.

This detector does not certify economic MATCH or remove residual stock effects.
It deliberately requires an explicit document reference and reports REVIEW only.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def _document(value: object) -> str:
    match = re.search(r"(?<!\d)(\d{3,})(?!\d)", str(value or ""))
    return match.group(1) if match else ""


def _day(value: object) -> str | None:
    text = str(value or "").strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _warehouse(row: dict[str, Any]) -> str | None:
    for key in ("Warehouse", "Gestiune"):
        value = str(row.get(key) or "").strip().casefold()
        if value:
            return " ".join(value.split())
    return None


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
        wdays = {_day(row.get("Data")) for row in referenced}
        edays = {_day(row.get("Date")) for row in pv_rows}
        dates_equal = None not in wdays | edays and len(wdays) == len(edays) == 1 and wdays == edays
        wh_wms = {_warehouse(row) for row in referenced}
        wh_wme = {_warehouse(row) for row in pv_rows}
        warehouses_equal = (
            None not in wh_wms | wh_wme
            and len(wh_wms) == len(wh_wme) == 1
            and wh_wms == wh_wme
        )
        source_rows = [row.get("SourceRowNumber") for row in referenced + pv_rows]
        provenance_complete = (
            all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in source_rows)
            and len(source_rows) == len(set(source_rows[:len(referenced)])) + len(set(source_rows[len(referenced):]))
        )
        # Identical quantities alone never prove a shared economic movement.
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
            "dates_equal": dates_equal,
            "warehouses_equal": warehouses_equal,
            "provenance_complete": provenance_complete,
            "reference_unique": len(referenced) == 1 and len(pv_rows) == 1,
            "status": "COR_STOC_PV_SOURCE_REVIEW",
            "economic_match": False,
            "stock_effect_verified": False,
            "human_validation": "NOT_ATTACHED",
        })
    return result

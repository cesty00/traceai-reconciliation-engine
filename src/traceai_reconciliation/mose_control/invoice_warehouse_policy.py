"""Invoice-level single-warehouse policy, independent of article identity.

Only negative WME F stock exits count; source-backed review, never auto-match.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Iterable, Mapping


def multi_warehouse_invoice_exits(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in events:
        if str(row.get("operation_type") or "").strip().upper() != "F":
            continue
        try:
            value = float(row["quantity"])
        except (TypeError, ValueError, KeyError):
            continue
        if not value < 0:
            continue
        document = str(row.get("document") or "").strip()
        day = str(row.get("date") or "").strip()
        partner = str(row.get("partner") or "").strip().upper()
        warehouse = str(row.get("warehouse") or "").strip().upper()
        source_row = row.get("source_row")
        if not all((document, day, partner, warehouse)) or not isinstance(source_row, int):
            continue
        grouped[(document, day, partner)].append(row)
    result = []
    for (document, day, partner), rows in grouped.items():
        warehouses = sorted({str(r["warehouse"]).strip().upper() for r in rows})
        if len(warehouses) <= 1:
            continue
        result.append({
            "status": "INVOICE_MULTI_WAREHOUSE_REVIEW",
            "verdict": "REVIEW",
            "invoice_document": document,
            "date": day,
            "partner": partner,
            "warehouses": warehouses,
            "source_rows": sorted({int(r["source_row"]) for r in rows}),
            "warning": "Single invoice has negative stock exits from multiple WME warehouses; human document review needed.",
        })
    return sorted(result, key=lambda x: (x["date"], x["invoice_document"]))

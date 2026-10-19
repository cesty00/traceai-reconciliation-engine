"""Identify WME invoice lines booked in more than one warehouse.

The same invoice number alone is insufficient; group by item, date, client,
unit and invoice document. This is a stock-ledger warning, not proof of
two fiscal invoices or of a mistaken shipment.
"""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable, Mapping


def cross_warehouse_invoice_exits(
    events: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for row in events:
        if str(row.get("operation_type", "")).strip().upper() != "F":
            continue
        try:
            amount = Decimal(str(row.get("quantity")))
        except (ValueError, TypeError, ArithmeticError):
            continue
        if not amount.is_finite() or amount >= 0:
            continue
        fields = ("document", "date", "product_name", "partner", "unit")
        identity = tuple(str(row.get(k) or "").strip().upper() for k in fields)
        if any(not x for x in identity):
            continue
        warehouse = str(row.get("warehouse") or "").strip().upper()
        if not warehouse or row.get("source_row") is None:
            continue
        grouped[identity].append((warehouse, str(amount), row.get("source_row")))
    findings = []
    for identity, lines in grouped.items():
        warehouses = sorted(set(x[0] for x in lines))
        if len(warehouses) < 2:
            continue
        findings.append({
            "status": "MULTI_WAREHOUSE_SAME_F_EXIT_REVIEW",
            "verdict": "REVIEW",
            "invoice_document": identity[0],
            "date": identity[1],
            "product_name": identity[2],
            "partner": identity[3],
            "unit": identity[4],
            "warehouses": warehouses,
            "source_rows": [x[2] for x in lines],
            "quantity_by_warehouse": {
                name: str(sum((Decimal(amount) for wh, amount, _ in lines if wh == name), Decimal("0")))
                for name in warehouses
            },
            "warning": "Same F stock impact in multiple WME warehouses. Not proof of duplicate fiscal invoice; inspect original F and document posting.",
        })
    return findings

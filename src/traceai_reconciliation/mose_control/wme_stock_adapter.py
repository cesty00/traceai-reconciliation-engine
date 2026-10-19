"""Fail-closed WME source adapter; does not invent lots or opening stock."""
from __future__ import annotations
from typing import Any, Iterable, Mapping

def clean(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    return "" if text.lower() in ("", "none", "nan", "-") else text

def adapt_wme_stock_rows(records: Iterable[Mapping[str, Any]], *,
                         require_lot: bool = True) -> dict[str, Any]:
    """Adapt explicit standardized WME fields, with complete provenance."""
    movements, blocked = [], []
    lot_coverage = "LOT" if require_lot else "ARTICLE_WAREHOUSE_ONLY"
    for index, row in enumerate(records):
        product, warehouse = clean(row.get("product_code")), clean(row.get("Warehouse"))
        lot, number = clean(row.get("Lot")), row.get("SourceRowNumber")
        if not product or not warehouse or not clean(row.get("Date")) or not clean(row.get("Document")):
            blocked.append({"index": index, "reason": "MISSING_SOURCE_IDENTITY"})
        elif require_lot and not lot:
            blocked.append({"index": index, "reason": "LOT_NOT_AVAILABLE"})
        elif not isinstance(number, int) or isinstance(number, bool) or number < 1:
            blocked.append({"index": index, "reason": "MISSING_PHYSICAL_SOURCE_ROW"})
        elif not clean(row.get("SignedQuantity")):
            blocked.append({"index": index, "reason": "MISSING_SIGNED_QUANTITY"})
        else:
            movements.append(dict(date=row.get("Date"), source_row=number,
                                  warehouse=warehouse, product_code=product,
                                  lot=lot, quantity=row.get("SignedQuantity"),
                                  document=row.get("Document"),
                                  operation_type=row.get("OperationType"),
                                  wme_reported_balance_unverified_scope=row.get("Balance")))
    if blocked:
        return {"status": "BLOCKED_WITH_REASON", "reasons": blocked, "movements": [], "verdict": "REVIEW"}
    return {"status": "ADAPTED_REVIEW", "movements": movements, "verdict": "REVIEW",
            "granularity": lot_coverage,
            "warning": "WME reported balance scope and opening stock need external verification."}

"""Bounded, read-only preliminary candidate indexing for MOSE pilot.

Input: normalized WME F and WMS delivery dictionaries. This is a triage
index, NEVER an invoice-to-delivery match. No inferred order ownership.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping


def _day(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _qty(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (ValueError, TypeError, InvalidOperation):
        return None


def _text(value: Any) -> str:
    return " ".join(str(value or "").upper().split())


def candidate_screen(
    invoices: Iterable[Mapping[str, Any]],
    deliveries: Iterable[Mapping[str, Any]],
    *,
    max_candidates_per_invoice: int = 25,
) -> list[dict[str, Any]]:
    """Return candidate counts and bounded source rows; never claim MATCH.

    Deliberately keys by EXACT normalized product name/date/absolute quantity.
    Never uses numeric WME item ID as a WMS code. Repeated source-row ownership
    across invoices is not consumed or resolved here.
    """
    if max_candidates_per_invoice < 1:
        raise ValueError("max_candidates_per_invoice must be positive")
    index: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in deliveries:
        if _text(row.get("operation_type")) not in ("LIVRARE", "DELIVERY"):
            continue
        if _text(row.get("order")).startswith("TRANSFER_MOSE"):
            continue
        name, day, qty = _text(row.get("product_name")), _day(row.get("date")), _qty(row.get("quantity"))
        if name and day is not None and qty is not None and qty < 0:
            index[(name, day, abs(qty))].append(row)

    result: list[dict[str, Any]] = []
    for invoice in invoices:
        name, day, qty = _text(invoice.get("product_name")), _day(invoice.get("date")), _qty(invoice.get("quantity"))
        candidates = index.get((name, day, abs(qty)), []) if name and day and qty is not None and qty < 0 else []
        result.append({
            "wme_document": invoice.get("document"),
            "wme_source_row": invoice.get("source_row"),
            "candidate_count": len(candidates),
            "candidate_wms_source_rows": [
                row.get("source_row") for row in candidates[:max_candidates_per_invoice]
            ],
            "candidates_truncated": len(candidates) > max_candidates_per_invoice,
            "status": "CANDIDATES_REVIEW" if candidates else "NO_SAME_DAY_CANDIDATE_REVIEW",
            "verdict": "REVIEW",
            "note": "Screening only: no cross-system document linkage, no MATCH, no global one-to-one ownership.",
        })
    return result

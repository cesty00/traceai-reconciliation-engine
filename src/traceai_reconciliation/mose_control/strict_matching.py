"""Strict, optional evidence check for an explicitly linked WME F / WMS delivery.

Read-only and fail-closed. The caller must supply a source-backed link
to the WMS document; product and quantity alone never establish ownership.
This module does not authorize an accounting or inventory correction.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence


def _text(value: Any) -> str:
    return str(value or "").strip().upper()


def _quantity(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _day(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def check_direct_delivery_link(
    invoice: Mapping[str, Any],
    wms_deliveries: Sequence[Mapping[str, Any]],
    *,
    explicit_wms_document: str | None,
    tolerance: str = "0.001",
) -> dict[str, Any]:
    """Return DOCUMENT_SUPPORTED_REVIEW only for one evidence-backed candidate.

    Both sides must provide product, signed quantity, date and row provenance;
    the invoice link must be explicit, never inferred from amount similarity.
    WMS transfer orders are excluded, including when their document is SFA.
    """
    ref = _text(explicit_wms_document)
    base = {"verdict": "REVIEW", "wms_document": ref or None, "wms_source_row": None}
    if not ref:
        return {**base, "status": "NO_EXPLICIT_LINK_REVIEW"}
    if _text(invoice.get("operation_type")) != "F":
        return {**base, "status": "INVALID_INVOICE_OPERATION_REVIEW"}
    inv_product = _text(invoice.get("product_code"))
    inv_qty = _quantity(invoice.get("quantity"))
    inv_date = _day(invoice.get("date"))
    inv_row = invoice.get("source_row")
    if not inv_product or inv_qty is None or inv_date is None or inv_row is None:
        return {**base, "status": "INCOMPLETE_INVOICE_EVIDENCE_REVIEW"}
    try:
        tol = Decimal(tolerance)
    except InvalidOperation:
        raise ValueError("Invalid tolerance")
    if not tol.is_finite() or tol < 0:
        raise ValueError("Invalid tolerance")

    candidates = [
        row for row in wms_deliveries
        if _text(row.get("document")) == ref
        and _text(row.get("operation_type")) in ("LIVRARE", "DELIVERY")
        and not _text(row.get("order")).startswith("TRANSFER_MOSE")
        and not _text(row.get("document")).startswith("TRANSFER_MOSE")
    ]
    if len(candidates) != 1:
        return {**base, "status": "LINK_MISSING_OR_AMBIGUOUS_REVIEW", "candidate_count": len(candidates)}
    wms = candidates[0]
    wms_qty = _quantity(wms.get("quantity"))
    wms_date = _day(wms.get("date"))
    if (not _text(wms.get("product_code"))
            or wms_qty is None or wms_date is None
            or wms.get("source_row") is None):
        return {**base, "status": "INCOMPLETE_WMS_EVIDENCE_REVIEW"}
    if _text(wms.get("product_code")) != inv_product:
        return {**base, "status": "PRODUCT_DIFFERENCE_REVIEW"}
    if wms_qty >= 0 or inv_qty >= 0 or abs(wms_qty - inv_qty) > tol:
        return {**base, "status": "QUANTITY_OR_DIRECTION_DIFFERENCE_REVIEW"}
    # Dates are checked, not assumed equivalent. Cross-date links require
    # further business rules and cannot be validated by this preliminary gate.
    if wms_date != inv_date:
        return {**base, "status": "DATE_DIFFERENCE_REVIEW"}
    return {
        **base,
        "status": "DOCUMENT_SUPPORTED_REVIEW",
        "wms_source_row": wms["source_row"],
        "wme_source_row": inv_row,
        "evidence": "Explicit document link, single WMS row, article, direction, amount and date agree.",
    }

"""Read-only, product-level WME invoice versus WMS delivery candidate screening.

Candidate arithmetic never proves a delivery-document correspondence.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Mapping, Sequence


def _qty(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def screen_invoice_delivery_quantities(
    invoice_rows: Sequence[Mapping[str, Any]],
    wms_candidates: Sequence[Mapping[str, Any]],
    *, candidates_truncated: bool = False,
) -> dict[str, Any]:
    wme = defaultdict(float)
    for row in invoice_rows:
        product = str(row.get("product_name") or "").strip().upper()
        amount = _qty(row.get("quantity"))
        if not product or amount is None:
            return {"status": "WME_QUANTITY_OR_PRODUCT_MISSING_REVIEW", "verdict": "REVIEW"}
        if amount < 0:
            wme[product] += -amount
    if not wme:
        return {"status": "NO_WME_INVOICE_OUTFLOWS_REVIEW", "verdict": "REVIEW"}
    wms = defaultdict(float)
    for row in wms_candidates:
        if row.get("candidate_class") != "DIRECT_DELIVERY_CANDIDATE":
            continue
        if row.get("partner_screen") != "PARTNER_CANDIDATE":
            continue
        product = str(row.get("product_name") or "").strip().upper()
        amount = _qty(row.get("quantity"))
        if not product or amount is None:
            continue
        wms[product] += abs(amount)
    items = []
    for product, expected in sorted(wme.items()):
        observed = wms.get(product, 0.0)
        if candidates_truncated:
            state = "SCREEN_TRUNCATED_REVIEW"
        elif observed == 0:
            state = "NO_CUSTOMER_DELIVERY_CANDIDATE_REVIEW"
        elif abs(observed - expected) <= 0.000001:
            state = "CANDIDATE_QUANTITIES_EQUAL_UNVERIFIED"
        else:
            state = "CANDIDATE_QUANTITIES_DIFFER_UNVERIFIED"
        items.append({"product_name": product, "wme_invoice_outgoing": expected,
                      "wms_customer_delivery_candidate_total": observed,
                      "candidate_difference": round(expected - observed, 6),
                      "status": state})
    return {
        "status": "QUANTITY_CANDIDATES_REVIEW", "verdict": "REVIEW",
        "automatic_match_allowed": False, "automatic_correction_allowed": False,
        "items": items,
        "notice": "Amounts are sums of candidate events, not proved invoice-linked deliveries.",
    }

"""Conservative WMS screening result for invoices posted by MOSE user from DP.

A candidate is not proof of customer delivery or an accounting error.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence


def assess_mose_direct_dp_invoice(invoice_rows: Sequence[Mapping[str, Any]],
                                   wms_candidates: Sequence[Mapping[str, Any]],
                                   *, truncated: bool = False) -> dict[str, Any]:
    warehouses = {str(x.get("warehouse") or "").strip().upper()
                  for x in invoice_rows if float(x.get("quantity") or 0) < 0}
    if not invoice_rows or warehouses not in ({"DEPOZIT PRINCIPAL"}, {"DP"}):
        return {"status": "NOT_SINGLE_DP_INVOICE", "verdict": "REVIEW"}
    direct = [x for x in wms_candidates
              if x.get("candidate_class") == "DIRECT_DELIVERY_CANDIDATE"
              and x.get("partner_screen") == "PARTNER_CANDIDATE"]
    internal = [x for x in wms_candidates
                if x.get("candidate_class") in ("TRANSFER_MOSE", "INTERNAL_ROUTE_REVIEW")]
    orders = sorted({str(x.get("document") or "").strip() for x in direct if x.get("document")})
    return {
        "status": ("WMS_SCREEN_INCOMPLETE_REVIEW" if truncated
                   else "DIRECT_CUSTOMER_DELIVERY_CANDIDATES_REVIEW" if direct
                   else "NO_DIRECT_CUSTOMER_DELIVERY_IN_SCREEN_REVIEW"),
        "candidate_wms_customer_orders": orders,
        "direct_candidate_rows": len(direct),
        "internal_transfer_candidate_rows": len(internal),
        "document_link": "NOT_VERIFIED", "verdict": "REVIEW",
        "posting_error_proven": False, "automatic_match_allowed": False,
        "automatic_correction_allowed": False,
        "note": "The WME warehouse alone is not proof of the physical WMS delivery.",
    }

"""Conservative document-level screening for WME invoice / WMS customer deliveries.

Never infer a document link from equal quantity, product, client or date.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Mapping, Sequence


def screen_delivery_document_links(
    invoice_rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    documents = defaultdict(list)
    for row in candidates:
        if row.get("candidate_class") != "DIRECT_DELIVERY_CANDIDATE":
            continue
        if row.get("partner_screen") != "PARTNER_CANDIDATE":
            continue
        order = str(row.get("document") or "").strip()
        if not order:
            continue
        documents[order].append(row)
    invoice_documents = {str(row.get("document") or "").strip() for row in invoice_rows}
    if len(invoice_documents) != 1 or not next(iter(invoice_documents)):
        return {"status": "INVOICE_DOCUMENT_AMBIGUOUS_REVIEW", "verdict": "REVIEW"}
    invoice_document = next(iter(invoice_documents))
    groups = []
    for order, rows in sorted(documents.items()):
        groups.append({
            "wms_order": order,
            "wms_source_rows": sorted({int(row["source_row"]) for row in rows
                                       if isinstance(row.get("source_row"), int)}),
            "candidate_item_count": len(rows),
            "link_status": "DOCUMENT_LINK_NOT_PROVEN",
        })
    return {
        "status": "DOCUMENT_LINK_SCREEN_REVIEW",
        "invoice_document": invoice_document,
        "customer_order_candidates": groups,
        "document_link_status": "NOT_VERIFIED",
        "verdict": "REVIEW",
        "automatic_match_allowed": False,
        "note": "Same customer/product/date/amount is not sufficient evidence of invoice-to-order linkage.",
    }

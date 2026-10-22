from __future__ import annotations

from typing import Any


def classify_receipt_for_operator(
    unsupported_receipts: list[dict[str, Any]],
    delivery_documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Read-only cross-module presentation. Never changes either matcher's result."""
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for document in delivery_documents:
        by_doc.setdefault(str(document.get("document", "")).strip(), []).append(document)

    classified: list[dict[str, Any]] = []
    for item in unsupported_receipts:
        raw = str(item.get("document", "")).strip()
        key = str(item.get("link_document", "")).strip()
        is_return = raw.upper().startswith(("RET_WME", "RET_SFA"))
        candidates = by_doc.get(key, []) if is_return and key else []
        status = "REVIEW"
        if is_return and len(candidates) == 1:
            candidate = candidates[0]
            # A net delivery MATCH is not proof that a return leg matches.
            # Promote only when the entire document consists of this return.
            qty = float(item.get("quantity") or 0)
            wms_qty = float(candidate.get("wms_net_quantity") or 0)
            wme_qty = float(candidate.get("wme_ae_quantity") or 0)
            if abs(wms_qty - qty) <= 0.001:
                status = (
                    "MATCH" if abs(wme_qty - qty) <= 0.001
                    else "QTY_DIFF"
                )
        classified.append({
            "document": raw,
            "link_document": key,
            "quantity": item.get("quantity"),
            "family": "RETURN_IN" if is_return else "RECEIPT_UNCLASSIFIED",
            "status": status,
            "evidence_status": "CROSS_MODULE" if len(candidates) == 1 else "REVIEW",
        })
    return classified

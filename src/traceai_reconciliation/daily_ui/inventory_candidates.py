"""Read-only projection of CORE inventory residuals into UI candidates.

Only emits candidates from unmatched inventory WMS residual groups.
Does not claim source-row provenance, document matching, or economic ownership.
"""
from collections import defaultdict
from typing import Mapping, Any

def inventory_document_candidates(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    details = case.get("details", {})
    inventory = details.get("inventory_adjustment_matching", {}) if isinstance(details, dict) else {}
    residuals = inventory.get("residual_wms_adjustments", []) if isinstance(inventory, dict) else []
    if not isinstance(residuals, list):
        raise ValueError("Invalid inventory residuals")
    groups = {}
    for residual in residuals:
        if not isinstance(residual, dict):
            raise ValueError("Invalid residual")
        events = residual.get("contributing_event_refs", [])
        if not isinstance(events, list):
            raise ValueError("Invalid contributing refs")
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("Invalid event ref")
            doc = event.get("document")
            if not isinstance(doc, str) or not doc.strip():
                continue
            qty = event.get("quantity")
            if isinstance(qty, bool) or not isinstance(qty, (int, float)):
                raise ValueError("Invalid inventory quantity")
            key = ("WMS", doc)
            group = groups.setdefault(key, {"system": "WMS", "document": doc, "events": []})
            group["events"].append({"quantity": float(qty), "lot": event.get("lot") or "-",
                                    "source_status": "UNVERIFIED"})
    return list(groups.values())

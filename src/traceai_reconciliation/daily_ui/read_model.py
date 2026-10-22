"""Read-only rendering model for existing daily_operator_result.json."""
from __future__ import annotations
from typing import Any, Mapping
from traceai_reconciliation.investigation.daily_operator import REQUIRED_OPERATOR_FIELDS

def operator_view(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("Invalid operator payload")
    absent = set(REQUIRED_OPERATOR_FIELDS) - set(payload)
    if absent:
        raise ValueError("Missing fields: " + ", ".join(sorted(absent)))
    if payload["wms_mutation_allowed"] is not False or payload["wme_mutation_allowed"] is not False:
        raise ValueError("Unsafe mutation authority")
    for key in ("difference", "residual"):
        if isinstance(payload[key], bool) or not isinstance(payload[key], (int, float)):
            raise ValueError("Invalid numerical field " + key)
    # The legacy Daily JSON lists generic rule descriptions, not verified
    # document IDs / physical rows. Never imply source-row validation.
    evidence = payload["evidence"]
    if not isinstance(evidence, (list, tuple)) or not all(isinstance(x, str) for x in evidence):
        raise ValueError("Invalid evidence field")
    documentary_status = "SOURCE_LINES_NOT_VERIFIED"
    candidates = payload.get("document_candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("Invalid document candidates")
    sanitized = []
    for item in candidates:
        if not isinstance(item, Mapping):
            raise ValueError("Invalid document candidate")
        if not item.get("document") or item.get("system") not in ("WMS", "WME"):
            raise ValueError("Incomplete document candidate")
        refs = item.get("events", [])
        if not isinstance(refs, list):
            raise ValueError("Invalid candidate events")
        events = []
        for event in refs:
            if not isinstance(event, Mapping) or isinstance(event.get("quantity"), bool) or not isinstance(event.get("quantity"), (int, float)):
                raise ValueError("Invalid event")
            events.append({"quantity": float(event["quantity"]), "lot": str(event.get("lot") or "-"),
                           "source_status": "UNVERIFIED"})
        sanitized.append({"system": item["system"], "document": str(item["document"]),
                          "events": events, "source_status": "UNVERIFIED",
                          "human_validation": "PENDING"})
    technical_receipts = payload.get("technical_receipts", [])
    if not isinstance(technical_receipts, list):
        raise ValueError("Invalid technical receipts")
    safe_receipts = []
    for receipt in technical_receipts:
        if not isinstance(receipt, Mapping):
            raise ValueError("Invalid technical receipt")
        if receipt.get("family") not in ("RETURN_IN", "RECEIPT_UNCLASSIFIED") or receipt.get("status") not in ("MATCH", "QTY_DIFF", "REVIEW"):
            raise ValueError("Invalid technical receipt classification")
        quantity = receipt.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, (int, float)):
            raise ValueError("Invalid technical receipt quantity")
        safe_receipts.append({
            "document": str(receipt.get("document") or ""),
            "link_document": str(receipt.get("link_document") or ""),
            "quantity": float(quantity),
            "family": receipt["family"],
            "status": receipt["status"],
            "human_validation": "PENDING",
        })
    return {
        "case_id": str(payload["case_id"]), "product_code": str(payload["product_code"]),
        "product_name": str(payload["product_name"]), "unit": str(payload["unit"]),
        "difference": float(payload["difference"]), "residual": float(payload["residual"]),
        "cause": str(payload["cause"]), "cause_status": str(payload["cause_status"]),
        "evidence_level": str(payload["evidence_level"]), "rules": list(payload["rules"]),
        "operator_status": str(payload["operator_status"]),
        "operator_action": str(payload["operator_action"]),
        "correction_target": str(payload["correction_target"]),
        "evidence": list(evidence), "blockers": list(payload["blockers"]),
        "warnings": list(payload["warnings"]), "documentary_validation": "NOT_AVAILABLE",
        "source_line_status": documentary_status,
        "document_candidates": sanitized, "technical_receipts": safe_receipts,
        "economic_match_authorized": False, "reviewer_validation_enabled": False,
    }

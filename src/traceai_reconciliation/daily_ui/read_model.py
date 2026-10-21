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
    return {
        "case_id": str(payload["case_id"]), "product_code": str(payload["product_code"]),
        "product_name": str(payload["product_name"]), "unit": str(payload["unit"]),
        "difference": float(payload["difference"]), "residual": float(payload["residual"]),
        "cause": str(payload["cause"]), "cause_status": str(payload["cause_status"]),
        "evidence_level": str(payload["evidence_level"]), "rules": list(payload["rules"]),
        "operator_status": str(payload["operator_status"]),
        "operator_action": str(payload["operator_action"]),
        "correction_target": str(payload["correction_target"]),
        "evidence": list(payload["evidence"]), "blockers": list(payload["blockers"]),
        "warnings": list(payload["warnings"]), "documentary_validation": "NOT_AVAILABLE",
        "economic_match_authorized": False, "reviewer_validation_enabled": False,
    }

"""CORE-UAT-03: isolated, read-only operator presentation prototype.

Not imported by the production application. Synthetic demonstrations only.
No reconciler, CaseReport, file, registry or economic status mutations.
"""
from __future__ import annotations

from typing import Any, Mapping

VALID_REASONS = frozenset({"INVENTORY", "OPERATION_ERROR", "OTHER", "UNKNOWN"})


def build_operator_display(
    automatic: Mapping[str, Any],
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a new display payload without modifying inputs.

    Automatic evidence attribution is not human validation or approval.
    Never infer validation from operator_status='CONFIRMAT'.
    """
    evidence = automatic.get("evidence", [])
    if not isinstance(evidence, (list, tuple)):
        raise ValueError("evidence must be a sequence")
    if not automatic.get("case_id") or not automatic.get("product_code"):
        raise ValueError("case_id and product_code required")
    if not isinstance(automatic.get("difference"), (int, float)):
        raise ValueError("numeric difference required")
    if not isinstance(automatic.get("residual"), (int, float)):
        raise ValueError("numeric residual required")
    if automatic.get("wms_mutation_allowed") is not False or automatic.get("wme_mutation_allowed") is not False:
        raise ValueError("read-only authority boundary required")

    source_items = [dict(item) for item in evidence if isinstance(item, dict)]
    has_identified_cause = bool(source_items) and all(
        item.get("source_hash") and item.get("document_ref")
        and isinstance(item.get("physical_row"), int) and item["physical_row"] > 0
        for item in source_items
    )
    attribution = "CAUSE_IDENTIFIED" if has_identified_cause else "REVIEW"
    validation_status = "OPERATIONAL_REVIEW"
    validation_record = None
    if validation is not None:
        reason = validation.get("reason_code", "UNKNOWN")
        if reason not in VALID_REASONS:
            raise ValueError("invalid reason_code")
        record = {
            "reason_code": reason,
            "comment": str(validation.get("comment") or ""),
            "supporting_document": str(validation.get("supporting_document") or ""),
            "reviewer": str(validation.get("reviewer") or ""),
            "validated_at": str(validation.get("validated_at") or ""),
            "scope": str(validation.get("scope") or ""),
        }
        # Require explicit reviewer assertion with traceable documentary support.
        if (has_identified_cause and reason != "UNKNOWN"
                and all(record[key].strip() for key in ("comment", "supporting_document", "reviewer", "validated_at", "scope"))):
            validation_status = "OPERATOR_VALIDATED"
        validation_record = record

    return {
        "case_id": automatic["case_id"],
        "product_code": automatic["product_code"],
        "difference": automatic["difference"],
        "residual": automatic["residual"],
        "attribution_status": attribution,
        "justification_status": validation_status,
        "automatic_evidence": source_items,
        "operator_statement": validation_record,
        "economic_verdict_unchanged": automatic.get("operator_status", "REVIEW"),
        "automatic_approval_allowed": False,
        "registry_apply_allowed": False,
        "wms_mutation_allowed": False,
        "wme_mutation_allowed": False,
        "report_annotation": "Operator rationale is not economic MATCH or adjustment authorization.",
    }

"""Validate MOSE review-queue JSON before presentation in Streamlit."""
from __future__ import annotations
from typing import Any


def validate_review_cases(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("MOSE review JSON must be an array")
    if len(payload) > 10000:
        raise ValueError("MOSE review list too large")
    validated = []
    seen = set()
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("Case must be an object")
        case_id = row.get("case_id")
        proof = row.get("evidence_source_rows")
        if not isinstance(case_id, str) or not case_id.startswith("MOSE-"):
            raise ValueError("Missing valid MOSE case id")
        if case_id in seen:
            raise ValueError("Duplicate case ID")
        seen.add(case_id)
        if row.get("engine_verdict") != "REVIEW" or row.get("automatic_correction_allowed") is not False:
            raise ValueError("Only read-only REVIEW cases supported")
        if not isinstance(proof, list) or not proof or any(
            not isinstance(x, int) or isinstance(x, bool) or x < 1 for x in proof
        ):
            raise ValueError("Missing original WME source rows")
        validated.append(row)
    return validated

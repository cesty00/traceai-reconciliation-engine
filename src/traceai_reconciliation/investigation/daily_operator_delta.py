from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .daily_delta_analysis import (
    DailyDeltaRootCauseItem,
    DailyDeltaRootCauseSummary,
)


def _event_text(item: dict[str, Any]) -> str:
    source = str(item.get("source") or "?")
    quantity = float(item.get("quantity") or 0.0)
    document = str(item.get("document") or "").strip()
    operation_type = str(item.get("operation_type") or "").strip()
    operation_date = str(item.get("operation_date") or "").strip()

    parts = [source, f"{quantity:+.3f}"]
    if operation_type:
        parts.append(operation_type)
    if document:
        parts.append(f"doc {document}")
    if operation_date:
        parts.append(operation_date)
    return " | ".join(parts)


def _operator_delta_payload(
    item: DailyDeltaRootCauseItem,
) -> dict[str, Any]:
    if item.status == "SKIPPED" or not item.analysis:
        return {
            "status": item.status,
            "reason": item.reason,
            "operator_action": (
                "Nu atribui cauza diferentei zilnice. Lipsesc limite temporale "
                "sau infrastructura necesara pentru analiza delta."
            ),
            "evidence": [],
        }

    root = item.analysis.get("root_cause", {})
    evidence = root.get("evidence", [])
    evidence_text = [
        _event_text(row)
        for row in evidence
        if isinstance(row, dict)
    ]

    status = str(root.get("status") or item.status)
    if status == "EXACT_EVENT":
        action = (
            "Verifica evenimentul identificat in sistemul sursa si documentul "
            "aferent. Corecteaza operational numai dupa confirmarea dovezii; "
            "nu replica automat miscarea."
        )
    elif status == "MULTI_EVENT":
        action = (
            "Verifica impreuna evenimentele identificate in fereastra delta. "
            "Confirma documentele sursa inainte de orice corectie operationala."
        )
    else:
        action = (
            "Delta nu este explicata integral de miscarile noi identificate. "
            "Pastreaza cazul in REVIEW si continua investigatia; nu forta MATCH."
        )

    return {
        "status": status,
        "reason": item.reason,
        "previous_difference": root.get("previous_difference"),
        "current_difference": root.get("current_difference"),
        "observed_delta": root.get("observed_delta"),
        "explained_delta": root.get("explained_delta"),
        "residual_delta": root.get("residual_delta"),
        "operator_action": action,
        "evidence": evidence_text,
    }


def enrich_daily_operator_artifacts(
    *,
    summary: DailyDeltaRootCauseSummary,
    cases_root: str | Path,
) -> tuple[str, ...]:
    """Attach daily delta context to existing read-only operator artifacts.

    Missing operator artifacts fail closed because the daily artifact gate
    requires them. This function never changes authority/mutation flags.
    """
    root = Path(cases_root)
    updated: list[str] = []

    for item in summary.items:
        if item.status == "SKIPPED" and item.reason == "SNAPSHOT_TIME_MISSING":
            # Still useful to tell the operator why no delta attribution exists.
            pass

        case_dir = root / item.case_id.replace("/", "_")
        operator_path = case_dir / "daily_operator_result.json"
        if not operator_path.is_file():
            continue

        payload = json.loads(operator_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(
                f"{item.case_id}: daily_operator_result.json is not an object."
            )

        payload["daily_delta"] = _operator_delta_payload(item)
        temporary = operator_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        temporary.replace(operator_path)
        updated.append(item.case_id)

    return tuple(updated)

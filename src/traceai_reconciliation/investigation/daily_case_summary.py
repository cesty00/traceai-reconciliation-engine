from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object.")
    return payload


def _compact_history(payload: dict[str, Any]) -> dict[str, Any]:
    history = payload.get("product_history")
    if not isinstance(history, dict):
        return {
            "history_status": "NO_HISTORY",
            "runs_available": 0,
            "recent_runs": [],
        }

    runs = history.get("runs")
    recent_runs = runs[:5] if isinstance(runs, list) else []
    return {
        "history_status": history.get("history_status"),
        "runs_available": history.get("runs_available", len(recent_runs)),
        "recent_runs": recent_runs,
    }


def build_daily_case_summary(
    *,
    run_id: str,
    operator_payload: dict[str, Any],
) -> dict[str, Any]:
    delta = operator_payload.get("daily_delta")
    delta_payload = delta if isinstance(delta, dict) else {
        "status": "NOT_AVAILABLE",
        "reason": "NO_DAILY_DELTA",
    }

    return {
        "schema_version": "1.0",
        "run_id": str(run_id),
        "case_id": operator_payload.get("case_id"),
        "product_code": operator_payload.get("product_code"),
        "product_name": operator_payload.get("product_name"),
        "unit": operator_payload.get("unit"),
        "difference": operator_payload.get("difference"),
        "cause": operator_payload.get("cause"),
        "cause_status": operator_payload.get("cause_status"),
        "evidence_level": operator_payload.get("evidence_level"),
        "correction_target": operator_payload.get("correction_target"),
        "operator_status": operator_payload.get("operator_status"),
        "operator_action": operator_payload.get("operator_action"),
        "residual": operator_payload.get("residual"),
        "daily_delta": delta_payload,
        "history": _compact_history(operator_payload),
        "evidence": operator_payload.get("evidence", []),
        "blockers": operator_payload.get("blockers", []),
        "warnings": operator_payload.get("warnings", []),
        "authority": {
            "human_decision_required": True,
            "automatic_approval_allowed": False,
            "registry_apply_allowed": False,
            "wms_mutation_allowed": False,
            "wme_mutation_allowed": False,
        },
    }


def write_daily_case_summaries(
    *,
    run_id: str,
    cases: Iterable[object],
    cases_root: str | Path,
) -> tuple[str, ...]:
    root = Path(cases_root)
    written: list[str] = []

    for case in cases:
        case_id = str(getattr(case, "case_id")).strip()
        case_dir = root / case_id.replace("/", "_")
        operator_path = case_dir / "daily_operator_result.json"
        if not operator_path.is_file():
            continue

        operator_payload = _load_json_object(operator_path)
        summary_payload = build_daily_case_summary(
            run_id=run_id,
            operator_payload=operator_payload,
        )
        summary_path = case_dir / "daily_case_summary.json"
        temporary = summary_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        temporary.replace(summary_path)
        written.append(case_id)

    return tuple(written)

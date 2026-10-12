from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from traceai_reconciliation.run_store import SQLiteRunStore


def _number(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_history(
    history: list[dict[str, object]],
    *,
    tolerance: float = 1e-6,
) -> str:
    """Classify the current difference using persisted run history only."""
    if not history:
        return "NO_HISTORY"
    if len(history) == 1:
        return "NEW_HISTORY"

    current = _number(history[0].get("current_difference"))
    previous = _number(history[1].get("current_difference"))
    if current is None or previous is None:
        return "UNKNOWN"

    current_zero = abs(current) <= tolerance
    previous_zero = abs(previous) <= tolerance

    if current_zero and not previous_zero:
        return "RESOLVED"
    if not current_zero and previous_zero:
        older_nonzero = any(
            (value := _number(item.get("current_difference"))) is not None
            and abs(value) > tolerance
            for item in history[2:]
        )
        return "REAPPEARED" if older_nonzero else "NEW_DIFFERENCE"
    if not current_zero and not previous_zero:
        if abs(current - previous) <= tolerance:
            return "PERSISTENT_UNCHANGED"
        return "PERSISTENT_CHANGED"
    return "ZERO_STABLE"


def build_operator_history_payload(
    *,
    product_code: str,
    history: list[dict[str, object]],
) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    for row in history:
        points.append(
            {
                "run_id": row.get("run_id"),
                "started_at": row.get("started_at"),
                "run_status": row.get("run_status"),
                "current_difference": row.get("current_difference"),
                "previous_difference": row.get("previous_difference"),
                "difference_delta": row.get("difference_delta"),
                "delta_status": row.get("delta_status"),
                "explained_delta": row.get("explained_delta"),
                "residual": row.get("residual"),
                "previous_run_id": row.get("previous_run_id"),
            }
        )

    return {
        "product_code": str(product_code).strip(),
        "history_status": classify_history(history),
        "runs_available": len(points),
        "runs": points,
    }


def enrich_operator_history_artifacts(
    *,
    run_store: SQLiteRunStore,
    cases: Iterable[object],
    cases_root: str | Path,
    limit: int = 10,
) -> tuple[str, ...]:
    """Attach persisted product history to existing operator JSON artifacts."""
    root = Path(cases_root)
    updated: list[str] = []

    for case in cases:
        case_id = str(getattr(case, "case_id")).strip()
        product_code = str(getattr(case, "product_code")).strip()
        operator_path = (
            root / case_id.replace("/", "_") / "daily_operator_result.json"
        )
        if not operator_path.is_file():
            continue

        payload = json.loads(operator_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(
                f"{case_id}: daily_operator_result.json is not an object."
            )

        history = run_store.get_product_history(product_code, limit=limit)
        payload["product_history"] = build_operator_history_payload(
            product_code=product_code,
            history=history,
        )

        temporary = operator_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        temporary.replace(operator_path)
        updated.append(case_id)

    return tuple(updated)

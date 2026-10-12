from __future__ import annotations

import json
from pathlib import Path

from traceai_reconciliation.investigation.daily_case_summary import (
    build_daily_case_summary,
    write_daily_case_summaries,
)


class Case:
    case_id = "CASE-1"


def test_build_daily_case_summary_combines_operator_delta_and_history() -> None:
    payload = build_daily_case_summary(
        run_id="RUN-2",
        operator_payload={
            "case_id": "CASE-1",
            "product_code": "DS099904475",
            "product_name": "Produs test",
            "unit": "KG",
            "difference": 61.46,
            "cause": "Cauza tehnica.",
            "cause_status": "DETERMINATA",
            "evidence_level": "A",
            "correction_target": "REVIEW",
            "operator_status": "REVIEW",
            "operator_action": "Verifica documentul.",
            "residual": 0.0,
            "daily_delta": {
                "status": "EXACT_EVENT",
                "observed_delta": -1.44,
                "explained_delta": -1.44,
                "residual_delta": 0.0,
            },
            "product_history": {
                "history_status": "PERSISTENT_CHANGED",
                "runs_available": 2,
                "runs": [
                    {"run_id": "RUN-2", "current_difference": 61.46},
                    {"run_id": "RUN-1", "current_difference": 62.9},
                ],
            },
            "evidence": ["WMS | -1.440 | AJUSTARE"],
            "blockers": [],
            "warnings": [],
        },
    )

    assert payload["run_id"] == "RUN-2"
    assert payload["daily_delta"]["status"] == "EXACT_EVENT"
    assert payload["history"]["history_status"] == "PERSISTENT_CHANGED"
    assert len(payload["history"]["recent_runs"]) == 2
    assert payload["authority"]["wms_mutation_allowed"] is False
    assert payload["authority"]["wme_mutation_allowed"] is False


def test_write_daily_case_summary_creates_artifact(tmp_path: Path) -> None:
    case_dir = tmp_path / "CASE-1"
    case_dir.mkdir()
    operator = {
        "case_id": "CASE-1",
        "product_code": "DS001",
        "product_name": "Produs",
        "unit": "KG",
        "difference": 1.0,
        "operator_status": "REVIEW",
        "operator_action": "Verifica.",
        "wms_mutation_allowed": False,
        "wme_mutation_allowed": False,
    }
    (case_dir / "daily_operator_result.json").write_text(
        json.dumps(operator),
        encoding="utf-8",
    )

    written = write_daily_case_summaries(
        run_id="RUN-1",
        cases=[Case()],
        cases_root=tmp_path,
    )

    path = case_dir / "daily_case_summary.json"
    assert written == ("CASE-1",)
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["daily_delta"]["status"] == "NOT_AVAILABLE"
    assert payload["history"]["history_status"] == "NO_HISTORY"

from __future__ import annotations

import json
from pathlib import Path

from traceai_reconciliation.investigation.daily_operator_history import (
    build_operator_history_payload,
    classify_history,
    enrich_operator_history_artifacts,
)
from traceai_reconciliation.run_store import CaseRecord, RunRecord, SQLiteRunStore


class Case:
    case_id = "CASE-1"
    product_code = "DS099904475"


def _history(*values: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, value in enumerate(values, start=1):
        rows.append(
            {
                "run_id": f"RUN-{index}",
                "started_at": f"2026-10-{20-index:02d}T20:00:00+00:00",
                "run_status": "SUCCESS",
                "current_difference": value,
                "previous_difference": None,
                "difference_delta": None,
                "delta_status": None,
                "explained_delta": None,
                "residual": None,
                "previous_run_id": None,
            }
        )
    return rows


def test_history_classification_persistent_changed() -> None:
    assert classify_history(_history(61.46, 62.9)) == "PERSISTENT_CHANGED"


def test_history_classification_resolved() -> None:
    assert classify_history(_history(0.0, 3.0)) == "RESOLVED"


def test_history_classification_reappeared() -> None:
    assert classify_history(_history(2.0, 0.0, 5.0)) == "REAPPEARED"


def test_operator_history_payload_keeps_delta_fields() -> None:
    history = [
        {
            "run_id": "RUN-2",
            "started_at": "2026-10-12T20:00:00+00:00",
            "run_status": "SUCCESS",
            "current_difference": 61.46,
            "previous_difference": 62.9,
            "difference_delta": -1.44,
            "delta_status": "EXACT_EVENT",
            "explained_delta": -1.44,
            "residual": 0.0,
            "previous_run_id": "RUN-1",
        }
    ]

    payload = build_operator_history_payload(
        product_code="DS099904475",
        history=history,
    )

    assert payload["history_status"] == "NEW_HISTORY"
    assert payload["runs"][0]["delta_status"] == "EXACT_EVENT"
    assert payload["runs"][0]["residual"] == 0.0


def test_enrich_operator_history_artifact_reads_run_store(tmp_path: Path) -> None:
    store = SQLiteRunStore(tmp_path / "state.sqlite")
    store.begin_run(
        RunRecord(
            run_id="RUN-1",
            started_at="2026-10-11T20:00:00+00:00",
            engine_version="0.10.0",
            rules_version="0.4",
            commit_sha="abc",
            signature=None,
            status="SUCCESS",
        )
    )
    store.save_case(
        CaseRecord(
            run_id="RUN-1",
            case_id="CASE-OLD",
            product_code="DS099904475",
            current_difference=62.9,
            previous_difference=None,
            difference_delta=None,
            execution_policy="ANALYZE",
        )
    )
    store.begin_run(
        RunRecord(
            run_id="RUN-2",
            started_at="2026-10-12T20:00:00+00:00",
            engine_version="0.10.0",
            rules_version="0.4",
            commit_sha="abc",
            signature=None,
            status="SUCCESS",
            previous_run_id="RUN-1",
        )
    )
    store.save_case(
        CaseRecord(
            run_id="RUN-2",
            case_id="CASE-1",
            product_code="DS099904475",
            current_difference=61.46,
            previous_difference=62.9,
            difference_delta=-1.44,
            execution_policy="ANALYZE",
            delta_status="EXACT_EVENT",
            explained_delta=-1.44,
            residual=0.0,
        )
    )

    case_dir = tmp_path / "cases" / "CASE-1"
    case_dir.mkdir(parents=True)
    operator_path = case_dir / "daily_operator_result.json"
    operator_path.write_text(
        json.dumps(
            {
                "case_id": "CASE-1",
                "product_code": "DS099904475",
                "wms_mutation_allowed": False,
                "wme_mutation_allowed": False,
            }
        ),
        encoding="utf-8",
    )

    updated = enrich_operator_history_artifacts(
        run_store=store,
        cases=[Case()],
        cases_root=tmp_path / "cases",
    )

    payload = json.loads(operator_path.read_text(encoding="utf-8"))
    assert updated == ("CASE-1",)
    assert payload["product_history"]["history_status"] == "PERSISTENT_CHANGED"
    assert payload["product_history"]["runs"][0]["run_id"] == "RUN-2"
    assert payload["product_history"]["runs"][0]["delta_status"] == "EXACT_EVENT"
    assert payload["wms_mutation_allowed"] is False
    assert payload["wme_mutation_allowed"] is False

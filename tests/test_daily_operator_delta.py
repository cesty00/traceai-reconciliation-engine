from __future__ import annotations

import json
from pathlib import Path

from traceai_reconciliation.investigation.daily_delta_analysis import (
    DailyDeltaRootCauseItem,
    DailyDeltaRootCauseSummary,
)
from traceai_reconciliation.investigation.daily_operator_delta import (
    enrich_daily_operator_artifacts,
)


def _summary(item: DailyDeltaRootCauseItem) -> DailyDeltaRootCauseSummary:
    return DailyDeltaRootCauseSummary(
        previous_snapshot_at="2026-10-11T20:00:00",
        current_snapshot_at="2026-10-12T20:00:00",
        analyzed=0 if item.status == "SKIPPED" else 1,
        skipped=1 if item.status == "SKIPPED" else 0,
        exact_event=1 if item.status == "EXACT_EVENT" else 0,
        multi_event=1 if item.status == "MULTI_EVENT" else 0,
        unexplained=1 if item.status == "UNEXPLAINED" else 0,
        items=(item,),
    )


def _operator_file(tmp_path: Path) -> Path:
    case_dir = tmp_path / "CASE-1"
    case_dir.mkdir()
    path = case_dir / "daily_operator_result.json"
    path.write_text(
        json.dumps(
            {
                "case_id": "CASE-1",
                "product_code": "DS099904475",
                "operator_status": "REVIEW",
                "wms_mutation_allowed": False,
                "wme_mutation_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_operator_delta_exact_event_is_visible_and_read_only(
    tmp_path: Path,
) -> None:
    path = _operator_file(tmp_path)
    item = DailyDeltaRootCauseItem(
        case_id="CASE-1",
        product_code="DS099904475",
        status="EXACT_EVENT",
        reason="ANALYZED",
        analysis={
            "root_cause": {
                "status": "EXACT_EVENT",
                "previous_difference": 62.9,
                "current_difference": 61.46,
                "observed_delta": -1.44,
                "explained_delta": -1.44,
                "residual_delta": 0.0,
                "evidence": [
                    {
                        "source": "WMS",
                        "quantity": -1.44,
                        "document": "ADJ-TEST",
                        "operation_type": "AJUSTARE",
                        "operation_date": "2026-10-12 10:00:00",
                    }
                ],
            }
        },
    )

    updated = enrich_daily_operator_artifacts(
        summary=_summary(item),
        cases_root=tmp_path,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert updated == ("CASE-1",)
    assert payload["daily_delta"]["status"] == "EXACT_EVENT"
    assert payload["daily_delta"]["observed_delta"] == -1.44
    assert payload["daily_delta"]["residual_delta"] == 0.0
    assert "ADJ-TEST" in payload["daily_delta"]["evidence"][0]
    assert payload["wms_mutation_allowed"] is False
    assert payload["wme_mutation_allowed"] is False


def test_operator_delta_unexplained_keeps_review_language(
    tmp_path: Path,
) -> None:
    path = _operator_file(tmp_path)
    item = DailyDeltaRootCauseItem(
        case_id="CASE-1",
        product_code="DS099904475",
        status="UNEXPLAINED",
        reason="ANALYZED",
        analysis={
            "root_cause": {
                "status": "UNEXPLAINED",
                "previous_difference": 62.9,
                "current_difference": 61.46,
                "observed_delta": -1.44,
                "explained_delta": -1.0,
                "residual_delta": -0.44,
                "evidence": [],
            }
        },
    )

    enrich_daily_operator_artifacts(
        summary=_summary(item),
        cases_root=tmp_path,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["daily_delta"]["status"] == "UNEXPLAINED"
    assert "nu forta MATCH" in payload["daily_delta"]["operator_action"]


def test_operator_delta_missing_snapshot_explains_skip(
    tmp_path: Path,
) -> None:
    path = _operator_file(tmp_path)
    item = DailyDeltaRootCauseItem(
        case_id="CASE-1",
        product_code="DS099904475",
        status="SKIPPED",
        reason="SNAPSHOT_TIME_MISSING",
        analysis=None,
    )

    enrich_daily_operator_artifacts(
        summary=_summary(item),
        cases_root=tmp_path,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["daily_delta"]["status"] == "SKIPPED"
    assert payload["daily_delta"]["reason"] == "SNAPSHOT_TIME_MISSING"

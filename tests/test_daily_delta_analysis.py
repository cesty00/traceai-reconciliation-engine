from pathlib import Path

from traceai_reconciliation.investigation.daily_delta import (
    DailyDeltaItem,
    DailyDeltaSummary,
)
from traceai_reconciliation.investigation.daily_delta_analysis import (
    analyze_daily_delta_root_causes,
)
from traceai_reconciliation.investigation.models import InvestigationSources


def _sources(tmp_path: Path, *, indexed: bool = True) -> InvestigationSources:
    return InvestigationSources(
        stock_report=tmp_path / "stock.xlsx",
        opening_stock_wms=tmp_path / "opening.xlsx",
        wms_movements=tmp_path / "wms.csv",
        wme_ledger=tmp_path / "wme.xlsx",
        production=tmp_path / "production.csv",
        nomenclature=tmp_path / "nomenclature.xlsx",
        cache_dir=tmp_path / "cache",
        use_source_index=indexed,
    )


def _changed_delta() -> DailyDeltaSummary:
    return DailyDeltaSummary(
        previous_run_id="RUN-1",
        new=0,
        changed=1,
        unchanged=0,
        items=(
            DailyDeltaItem(
                case_id="CASE-1",
                product_code="DS099904475",
                status="CHANGED",
                previous_difference=62.9,
                current_difference=61.46,
                difference_delta=-1.44,
                execution_policy="ANALYZE",
                note="changed",
            ),
        ),
    )


def test_daily_delta_root_cause_skips_when_snapshot_time_missing(
    tmp_path: Path,
) -> None:
    result = analyze_daily_delta_root_causes(
        delta=_changed_delta(),
        current_snapshot_state={
            "CASE-1": {
                "product_code": "DS099904475",
                "product_name": "Produs test",
            }
        },
        previous_snapshot_at=None,
        current_snapshot_at="2026-10-12T20:00:00",
        sources=_sources(tmp_path),
    )

    assert result.analyzed == 0
    assert result.skipped == 1
    assert result.items[0].reason == "SNAPSHOT_TIME_MISSING"


def test_daily_delta_root_cause_skips_when_index_disabled(
    tmp_path: Path,
) -> None:
    result = analyze_daily_delta_root_causes(
        delta=_changed_delta(),
        current_snapshot_state={
            "CASE-1": {
                "product_code": "DS099904475",
                "product_name": "Produs test",
            }
        },
        previous_snapshot_at="2026-10-11T20:00:00",
        current_snapshot_at="2026-10-12T20:00:00",
        sources=_sources(tmp_path, indexed=False),
    )

    assert result.analyzed == 0
    assert result.skipped == 1
    assert result.items[0].reason == "SOURCE_INDEX_DISABLED"


def test_daily_delta_root_cause_ignores_unchanged_cases(tmp_path: Path) -> None:
    delta = DailyDeltaSummary(
        previous_run_id="RUN-1",
        new=0,
        changed=0,
        unchanged=1,
        items=(
            DailyDeltaItem(
                case_id="CASE-1",
                product_code="DS1",
                status="UNCHANGED",
                previous_difference=1.0,
                current_difference=1.0,
                difference_delta=0.0,
                execution_policy="REUSE_SAFE",
                note="same",
            ),
        ),
    )

    result = analyze_daily_delta_root_causes(
        delta=delta,
        current_snapshot_state={},
        previous_snapshot_at=None,
        current_snapshot_at=None,
        sources=_sources(tmp_path),
    )

    assert result.analyzed == 0
    assert result.skipped == 0
    assert result.items == ()

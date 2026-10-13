from pathlib import Path
from types import SimpleNamespace
from dataclasses import dataclass

from traceai_reconciliation.investigation import daily_delta_analysis as mod
from traceai_reconciliation.investigation.daily_delta import DailyDeltaItem, DailyDeltaSummary
from traceai_reconciliation.investigation.models import InvestigationSources


@dataclass
class FakeWindow:
    wms_rows: tuple = ()
    wme_rows: tuple = ()
    production_rows: tuple = ()


@dataclass
class FakeRootCause:
    status: str = "UNEXPLAINED"
    note: str = "review"


def test_daily_only_passes_verified_aggregate_scope(monkeypatch, tmp_path: Path):
    class FakeIndex:
        def __init__(self, cache_dir):
            pass
        def ensure_index(self, *paths):
            pass

    monkeypatch.setattr(mod, "SQLiteSourceIndex", FakeIndex)
    monkeypatch.setattr(
        mod, "build_delta_movement_window",
        lambda **kwargs: FakeWindow(),
    )
    received = []
    def capture(**kwargs):
        received.append(kwargs.get("stock_scope"))
        return FakeRootCause()
    monkeypatch.setattr(mod, "analyze_delta_root_cause", capture)
    delta = DailyDeltaSummary(
        previous_run_id="R1", new=0, changed=1, unchanged=0,
        items=(DailyDeltaItem("C1","10002","CHANGED",1.0,2.0,1.0,"ANALYZE","changed"),),
    )
    sources = InvestigationSources(
        stock_report=tmp_path/"stock.xlsx",
        opening_stock_wms=tmp_path/"opening.xlsx",
        wms_movements=tmp_path/"wms.csv",
        wme_ledger=tmp_path/"wme.xlsx",
        production=tmp_path/"production.csv",
        nomenclature=tmp_path/"nomenclature.xlsx",
        cache_dir=tmp_path/"cache",
        use_source_index=True,
    )
    for state in (
        {"product_name":"CUTIE FRESH", "stock_scope":"AGGREGATE"},
        {"product_name":"CUTIE FRESH", "stock_scope":"AGGREGATE", "stock_scope_verified":False},
        {"product_name":"CUTIE FRESH", "stock_scope":"AGGREGATE", "stock_scope_verified":True},
    ):
        mod.analyze_daily_delta_root_causes(
            delta=delta, current_snapshot_state={"C1":state},
            previous_snapshot_at="2026-10-11T20:00:00",
            current_snapshot_at="2026-10-12T20:00:00",
            sources=sources,
        )
    assert received == [None,None,"AGGREGATE"]

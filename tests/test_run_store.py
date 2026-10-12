from pathlib import Path

from traceai_reconciliation.run_store import CaseRecord, RunRecord, SQLiteRunStore


def test_run_store_roundtrip(tmp_path: Path) -> None:
    store = SQLiteRunStore(tmp_path / "traceai_state.sqlite")
    store.begin_run(
        RunRecord(
            run_id="RUN-1",
            started_at="2026-10-12T20:00:00+00:00",
            engine_version="0.10.0",
            rules_version="0.4",
            commit_sha="abc123",
            signature=None,
            status="RUNNING",
        )
    )
    store.save_case(
        CaseRecord(
            run_id="RUN-1",
            case_id="CASE-1",
            product_code="DS099904475",
            current_difference=61.46,
            previous_difference=62.9,
            difference_delta=-1.44,
            execution_policy="REANALYZE_SOURCE_CHANGED",
        )
    )

    run = store.get_run("RUN-1")
    case = store.get_case("RUN-1", "CASE-1")

    assert run is not None
    assert run["status"] == "RUNNING"
    assert case is not None
    assert case["product_code"] == "DS099904475"
    assert case["difference_delta"] == -1.44

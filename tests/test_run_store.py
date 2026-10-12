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


def test_run_store_persists_delta_outcome_and_history(tmp_path: Path) -> None:
    store = SQLiteRunStore(tmp_path / "traceai_state.sqlite")

    for run_id, started_at, current, previous, status, explained, residual in (
        (
            "RUN-1",
            "2026-10-11T20:00:00+00:00",
            62.9,
            None,
            None,
            None,
            None,
        ),
        (
            "RUN-2",
            "2026-10-12T20:00:00+00:00",
            61.46,
            62.9,
            "EXACT_EVENT",
            -1.44,
            0.0,
        ),
    ):
        store.begin_run(
            RunRecord(
                run_id=run_id,
                started_at=started_at,
                engine_version="0.10.0",
                rules_version="0.4",
                commit_sha="abc123",
                signature=None,
                status="SUCCESS",
                previous_run_id="RUN-1" if run_id == "RUN-2" else None,
            )
        )
        store.save_case(
            CaseRecord(
                run_id=run_id,
                case_id=f"CASE-{run_id}",
                product_code="DS099904475",
                current_difference=current,
                previous_difference=previous,
                difference_delta=(
                    None if previous is None else current - previous
                ),
                execution_policy="ANALYZE",
                delta_status=status,
                explained_delta=explained,
                residual=residual,
            )
        )

    history = store.get_product_history("DS099904475")

    assert [item["run_id"] for item in history] == ["RUN-2", "RUN-1"]
    assert history[0]["delta_status"] == "EXACT_EVENT"
    assert round(float(history[0]["explained_delta"]), 6) == -1.44
    assert round(float(history[0]["residual"]), 6) == 0.0
    assert history[0]["previous_run_id"] == "RUN-1"


def test_run_store_migrates_schema_v1_to_v2(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "traceai_state.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE _schema_meta (
                schema_version INTEGER NOT NULL
            );
            INSERT INTO _schema_meta(schema_version) VALUES (1);

            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                engine_version TEXT NOT NULL,
                rules_version TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                signature TEXT,
                status TEXT NOT NULL,
                previous_run_id TEXT
            );

            CREATE TABLE sources (
                run_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                PRIMARY KEY (run_id, source_type)
            );

            CREATE TABLE cases (
                run_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                product_code TEXT NOT NULL,
                current_difference REAL,
                previous_difference REAL,
                difference_delta REAL,
                execution_policy TEXT,
                status TEXT,
                cause_code TEXT,
                evidence_level TEXT,
                residual REAL,
                operator_action TEXT,
                correction_target TEXT,
                PRIMARY KEY (run_id, case_id)
            );
            """
        )

    store = SQLiteRunStore(path)
    store.initialize()

    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT schema_version FROM _schema_meta"
        ).fetchone()[0]
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(cases)"
            ).fetchall()
        }

    assert version == 2
    assert "delta_status" in columns
    assert "explained_delta" in columns

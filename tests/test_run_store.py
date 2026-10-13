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
            snapshot_at="2026-10-12T20:00:00+00:00",
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
    assert run["snapshot_at"] == "2026-10-12T20:00:00+00:00"
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


def test_run_store_migrates_schema_v1_to_current(tmp_path: Path) -> None:
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

    assert version == 3
    assert "delta_status" in columns
    assert "explained_delta" in columns

    with sqlite3.connect(path) as connection:
        run_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(runs)"
            ).fetchall()
        }
    assert "snapshot_at" in run_columns


def test_run_store_migrates_schema_v2_to_v3_snapshot_at(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "traceai_state.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE _schema_meta (
                schema_version INTEGER NOT NULL
            );
            INSERT INTO _schema_meta(schema_version) VALUES (2);

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
                delta_status TEXT,
                explained_delta REAL,
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
        run_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(runs)"
            ).fetchall()
        }

    assert version == 3
    assert "snapshot_at" in run_columns


def test_product_history_exposes_snapshot_at(tmp_path: Path) -> None:
    store = SQLiteRunStore(tmp_path / "traceai_state.sqlite")
    store.begin_run(
        RunRecord(
            run_id="RUN-1",
            started_at="2026-10-12T20:05:00+00:00",
            engine_version="0.10.0",
            rules_version="0.4",
            commit_sha="abc123",
            signature=None,
            status="SUCCESS",
            snapshot_at="2026-10-12T20:00:00+00:00",
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
            execution_policy="ANALYZE",
        )
    )

    history = store.get_product_history("DS099904475")

    assert history[0]["snapshot_at"] == "2026-10-12T20:00:00+00:00"


def test_run_store_returns_latest_successful_run_and_snapshot_state(
    tmp_path: Path,
) -> None:
    store = SQLiteRunStore(tmp_path / "traceai_state.sqlite")

    store.begin_run(
        RunRecord(
            run_id="RUN-OLD",
            started_at="2026-10-11T20:05:00+00:00",
            engine_version="0.10.0",
            rules_version="0.4",
            commit_sha="abc",
            signature="sig-old",
            status="SUCCESS",
            snapshot_at="2026-10-11T20:00:00+00:00",
        )
    )
    store.save_sources(
        [
            SourceRecord(
                run_id="RUN-OLD",
                source_type="wms_movements",
                file_name="wms.csv",
                size=10,
                sha256="hash-wms",
            )
        ]
    )
    store.save_case(
        CaseRecord(
            run_id="RUN-OLD",
            case_id="CASE-1",
            product_code="DS001",
            current_difference=3.5,
            previous_difference=None,
            difference_delta=None,
            execution_policy="ANALYZE",
        )
    )

    store.begin_run(
        RunRecord(
            run_id="RUN-FAILED",
            started_at="2026-10-12T20:05:00+00:00",
            engine_version="0.10.0",
            rules_version="0.4",
            commit_sha="abc",
            signature="sig-failed",
            status="FAILED_SAFE",
            snapshot_at="2026-10-12T20:00:00+00:00",
        )
    )

    latest = store.get_latest_successful_run()

    assert latest is not None
    assert latest["run_id"] == "RUN-OLD"
    assert latest["snapshot_at"] == "2026-10-11T20:00:00+00:00"
    assert store.get_source_hashes("RUN-OLD") == {
        "wms_movements": "hash-wms"
    }
    assert store.get_snapshot_state("RUN-OLD") == {
        "CASE-1": {
            "case_id": "CASE-1",
            "product_code": "DS001",
            "difference_reported": 3.5,
        }
    }


def test_latest_successful_run_can_exclude_current_run(tmp_path: Path) -> None:
    store = SQLiteRunStore(tmp_path / "traceai_state.sqlite")
    for run_id, started in (
        ("RUN-1", "2026-10-11T20:05:00+00:00"),
        ("RUN-2", "2026-10-12T20:05:00+00:00"),
    ):
        store.begin_run(
            RunRecord(
                run_id=run_id,
                started_at=started,
                engine_version="0.10.0",
                rules_version="0.4",
                commit_sha="abc",
                signature=f"sig-{run_id}",
                status="SUCCESS",
            )
        )

    latest = store.get_latest_successful_run(exclude_run_id="RUN-2")

    assert latest is not None
    assert latest["run_id"] == "RUN-1"

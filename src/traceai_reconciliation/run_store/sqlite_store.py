from __future__ import annotations

from pathlib import Path
import sqlite3

from .models import CaseRecord, RunRecord, SourceRecord


SCHEMA_VERSION = 3


class SQLiteRunStore:
    """Persistent metadata store for daily runs.

    RAW WMS/WME files remain external. The store keeps only run metadata,
    source identities, case deltas and investigation outcomes.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS _schema_meta (
                    schema_version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    engine_version TEXT NOT NULL,
                    rules_version TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    signature TEXT,
                    status TEXT NOT NULL,
                    snapshot_at TEXT,
                    previous_run_id TEXT
                );

                CREATE TABLE IF NOT EXISTS sources (
                    run_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    PRIMARY KEY (run_id, source_type),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS cases (
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
                    PRIMARY KEY (run_id, case_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_cases_product
                    ON cases(product_code);
                CREATE INDEX IF NOT EXISTS idx_runs_started
                    ON runs(started_at);
                """
            )
            row = connection.execute(
                "SELECT schema_version FROM _schema_meta LIMIT 1"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO _schema_meta(schema_version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            else:
                version = int(row[0])
                if version == 1:
                    columns = {
                        item[1]
                        for item in connection.execute(
                            "PRAGMA table_info(cases)"
                        ).fetchall()
                    }
                    if "delta_status" not in columns:
                        connection.execute(
                            "ALTER TABLE cases ADD COLUMN delta_status TEXT"
                        )
                    if "explained_delta" not in columns:
                        connection.execute(
                            "ALTER TABLE cases ADD COLUMN explained_delta REAL"
                        )
                    version = 2
                    connection.execute(
                        "UPDATE _schema_meta SET schema_version = ?",
                        (version,),
                    )

                if version == 2:
                    run_columns = {
                        item[1]
                        for item in connection.execute(
                            "PRAGMA table_info(runs)"
                        ).fetchall()
                    }
                    if "snapshot_at" not in run_columns:
                        connection.execute(
                            "ALTER TABLE runs ADD COLUMN snapshot_at TEXT"
                        )
                    version = 3
                    connection.execute(
                        "UPDATE _schema_meta SET schema_version = ?",
                        (version,),
                    )

                if version != SCHEMA_VERSION:
                    raise RuntimeError(
                        "Unsupported run-store schema version: "
                        f"{version} (expected {SCHEMA_VERSION})"
                    )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        self.initialize()
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def begin_run(self, run: RunRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    run_id, started_at, finished_at, engine_version,
                    rules_version, commit_sha, signature, status,
                    snapshot_at, previous_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    engine_version=excluded.engine_version,
                    rules_version=excluded.rules_version,
                    commit_sha=excluded.commit_sha,
                    signature=excluded.signature,
                    status=excluded.status,
                    snapshot_at=excluded.snapshot_at,
                    previous_run_id=excluded.previous_run_id
                """,
                (
                    run.run_id,
                    run.started_at,
                    run.finished_at,
                    run.engine_version,
                    run.rules_version,
                    run.commit_sha,
                    run.signature,
                    run.status,
                    run.snapshot_at,
                    run.previous_run_id,
                ),
            )

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        finished_at: str,
        signature: str | None = None,
    ) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE runs
                SET status = ?, finished_at = ?, signature = COALESCE(?, signature)
                WHERE run_id = ?
                """,
                (status, finished_at, signature, run_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown run_id: {run_id}")

    def save_sources(self, records: list[SourceRecord]) -> None:
        if not records:
            return
        run_ids = {record.run_id for record in records}
        if len(run_ids) != 1:
            raise ValueError("All source records must belong to one run.")
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO sources (
                    run_id, source_type, file_name, size, sha256
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id, source_type) DO UPDATE SET
                    file_name=excluded.file_name,
                    size=excluded.size,
                    sha256=excluded.sha256
                """,
                [
                    (
                        item.run_id,
                        item.source_type,
                        item.file_name,
                        item.size,
                        item.sha256,
                    )
                    for item in records
                ],
            )

    def save_case(self, record: CaseRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cases (
                    run_id, case_id, product_code, current_difference,
                    previous_difference, difference_delta, execution_policy,
                    delta_status, explained_delta, status, cause_code,
                    evidence_level, residual, operator_action, correction_target
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, case_id) DO UPDATE SET
                    product_code=excluded.product_code,
                    current_difference=excluded.current_difference,
                    previous_difference=excluded.previous_difference,
                    difference_delta=excluded.difference_delta,
                    execution_policy=excluded.execution_policy,
                    delta_status=excluded.delta_status,
                    explained_delta=excluded.explained_delta,
                    status=excluded.status,
                    cause_code=excluded.cause_code,
                    evidence_level=excluded.evidence_level,
                    residual=excluded.residual,
                    operator_action=excluded.operator_action,
                    correction_target=excluded.correction_target
                """,
                (
                    record.run_id,
                    record.case_id,
                    record.product_code,
                    record.current_difference,
                    record.previous_difference,
                    record.difference_delta,
                    record.execution_policy,
                    record.delta_status,
                    record.explained_delta,
                    record.status,
                    record.cause_code,
                    record.evidence_level,
                    record.residual,
                    record.operator_action,
                    record.correction_target,
                ),
            )

    def get_run(self, run_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def get_previous_run(self, run_id: str) -> dict[str, object] | None:
        current = self.get_run(run_id)
        if current is None:
            return None
        previous_run_id = current.get("previous_run_id")
        if not previous_run_id:
            return None
        return self.get_run(str(previous_run_id))

    def get_case(
        self,
        run_id: str,
        case_id: str,
    ) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM cases
                WHERE run_id = ? AND case_id = ?
                """,
                (run_id, case_id),
            ).fetchone()
        return dict(row) if row is not None else None

    def get_product_history(
        self,
        product_code: str,
        *,
        limit: int = 30,
    ) -> list[dict[str, object]]:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.*,
                    r.started_at,
                    r.finished_at,
                    r.status AS run_status,
                    r.snapshot_at,
                    r.previous_run_id
                FROM cases c
                JOIN runs r ON r.run_id = c.run_id
                WHERE c.product_code = ?
                ORDER BY r.started_at DESC, c.run_id DESC
                LIMIT ?
                """,
                (str(product_code).strip(), int(limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_latest_case_for_product(
        self,
        product_code: str,
    ) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT c.*
                FROM cases c
                JOIN runs r ON r.run_id = c.run_id
                WHERE c.product_code = ?
                ORDER BY r.started_at DESC, c.run_id DESC
                LIMIT 1
                """,
                (product_code,),
            ).fetchone()
        return dict(row) if row is not None else None

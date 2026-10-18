"""Append-only local audit register for generated TraceAI operator reports.

This is *not* the human approval/registry_update ledger. Recording a run
never changes review authority or WMS/WME stock.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import re
import sqlite3
from uuid import uuid4


def registry_root() -> Path:
    return Path.home() / "TraceAI" / "operator_registry"


def _connect(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(root / "verificari.sqlite3", timeout=30)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS report_runs (
            run_id TEXT PRIMARY KEY,
            recorded_at TEXT NOT NULL,
            case_id TEXT NOT NULL,
            product_code TEXT NOT NULL,
            product_name TEXT,
            period TEXT NOT NULL,
            difference REAL,
            unit TEXT,
            engine_verdict TEXT NOT NULL,
            generated_at TEXT,
            engine_version TEXT,
            rules_version TEXT,
            engine_commit_sha TEXT,
            source_hashes_json TEXT,
            archive_dir TEXT NOT NULL,
            docx_path TEXT NOT NULL,
            json_path TEXT NOT NULL,
            summary_path TEXT NOT NULL
        )
    """)
    return connection


def report_filename(product_code: str, run_id: str, extension: str) -> str:
    """Windows-safe filename for archive and download."""
    code = re.sub(r"[^A-Za-z0-9_-]", "_", str(product_code).strip())
    if not code or not re.fullmatch(r"[A-Za-z0-9_-]+", str(run_id)):
        raise ValueError("Cod articol / ID verificare invalid.")
    if extension not in ("docx", "json"):
        raise ValueError("Extensie neacceptată.")
    return f"TraceAI_{code}_{run_id}.{extension}"


def record_generated_report(summary_path: str | Path, *, root: str | Path | None = None) -> str:
    """Archive outputs and append a run only after all three output files exist.

    A unique run_id is used rather than CASE-SELF-{product}, preserving history.
    On database failure the existing entries remain untouched.
    """
    src = Path(summary_path)
    summary = json.loads(src.read_text(encoding="utf-8"))
    paths = summary.get("outputs") or {}
    files = {
        "case.docx": Path(paths["case_docx"]),
        "case.json": Path(paths["case_json"]),
        "self_service_summary.json": src,
    }
    for source in files.values():
        if not source.is_file():
            raise FileNotFoundError(f"Registru verificări: fișier lipsă: {source}")
    technical = json.loads(files["case.json"].read_text(encoding="utf-8"))
    inv = technical.get("investigation") or {}
    readiness = technical.get("source_readiness") or {}
    root_path = Path(root) if root is not None else registry_root()
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid4().hex[:12]}"
    archive = root_path / "reports" / run_id
    archive.mkdir(parents=True, exist_ok=False)
    report_base = {
        "case.docx": report_filename(summary["product_code"], run_id, "docx"),
        "case.json": report_filename(summary["product_code"], run_id, "json"),
        "self_service_summary.json": "self_service_summary.json",
    }
    for filename, original in files.items():
        shutil.copy2(original, archive / report_base[filename])
    row = (
        run_id, datetime.now(timezone.utc).isoformat(timespec="seconds"),
        str(summary["case_id"]), str(summary["product_code"]),
        str(inv.get("product_name") or ""), str(summary["period"]),
        float(inv["initial_difference"]) if inv.get("initial_difference") is not None else None,
        str(inv.get("unit") or ""), str(summary.get("verdict") or "REVIEW"),
        str(summary.get("generated_at") or ""),
        str(summary.get("engine_version") or ""), str(summary.get("rules_version") or ""),
        str(summary.get("engine_commit_sha") or ""),
        json.dumps(readiness.get("source_hashes") or {}, sort_keys=True),
        str(archive), str(archive / report_base["case.docx"]), str(archive / report_base["case.json"]),
        str(archive / "self_service_summary.json"),
    )
    with _connect(root_path) as db:
        db.execute("""
            INSERT INTO report_runs (
                run_id, recorded_at, case_id, product_code, product_name,
                period, difference, unit, engine_verdict, generated_at,
                engine_version, rules_version, engine_commit_sha,
                source_hashes_json, archive_dir, docx_path, json_path, summary_path
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, row)
    return run_id


def list_generated_reports(*, root: str | Path | None = None, limit: int = 1000) -> list[dict]:
    root_path = Path(root) if root is not None else registry_root()
    with _connect(root_path) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM report_runs ORDER BY recorded_at DESC, run_id DESC LIMIT ?",
            (max(1, min(int(limit), 10000)),),
        ).fetchall()
    return [dict(row) for row in rows]

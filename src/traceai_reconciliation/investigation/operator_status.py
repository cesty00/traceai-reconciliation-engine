"""Human-only, append-only operator decisions per product and warehouse."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4

from .operator_report_registry import registry_root

STATUSES = (
    "NEVERIFICAT", "IN_ANALIZA", "VERIFICARE_SUPLIMENTARA",
    "CAUZA_CONFIRMATA", "CORECTIE_EFECTUATA", "REVERIFICAT_INCHIS",
)

def _db(root: str | Path | None = None):
    target = Path(root) if root is not None else registry_root()
    target.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target / "verificari.sqlite3", timeout=30)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS operator_decisions (
          event_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
          product_code TEXT NOT NULL, warehouse TEXT NOT NULL,
          status TEXT NOT NULL, operator_user TEXT NOT NULL,
          observation TEXT NOT NULL, report_run_id TEXT
        )
    """)
    return conn

def set_operator_status(*, product_code: str, warehouse: str, status: str,
                        operator_user: str, observation: str = "",
                        report_run_id: str | None = None,
                        root: str | Path | None = None) -> str:
    if status not in STATUSES or status == "NEVERIFICAT":
        raise ValueError("Status invalid sau implicit; schimbarea trebuie explicită.")
    if not all(str(value).strip() for value in (product_code, warehouse, operator_user)):
        raise ValueError("Articolul, gestiunea și utilizatorul sunt obligatorii.")
    if status == "REVERIFICAT_INCHIS":
        if not str(observation).strip():
            raise ValueError("Închiderea necesită observație și verificare documentată.")
        if not str(report_run_id or "").strip():
            raise ValueError("Închiderea necesită un raport TraceAI arhivat.")
    event_id = uuid4().hex
    with _db(root) as conn:
        if report_run_id:
            match = conn.execute(
                "SELECT product_code FROM report_runs WHERE run_id = ?",
                (report_run_id,),
            ).fetchone() if _has_reports(conn) else None
            if match is None or match[0] != product_code:
                raise ValueError("Raportul asociat nu există sau aparține altui articol.")
        conn.execute(
            "INSERT INTO operator_decisions VALUES (?,?,?,?,?,?,?,?)",
            (event_id, datetime.now(timezone.utc).isoformat(timespec="microseconds"),
             product_code.strip(), warehouse.strip(), status, operator_user.strip(),
             observation.strip(), report_run_id),
        )
    return event_id

def _has_reports(conn):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='report_runs'").fetchone() is not None

def list_operator_statuses(*, root: str | Path | None = None) -> list[dict]:
    with _db(root) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM operator_decisions ORDER BY created_at DESC, event_id DESC").fetchall()
    return [dict(row) for row in rows]

def latest_operator_statuses(*, root: str | Path | None = None) -> dict[tuple[str,str],dict]:
    latest = {}
    for row in list_operator_statuses(root=root):
        latest.setdefault((row["product_code"], row["warehouse"]), row)
    return latest

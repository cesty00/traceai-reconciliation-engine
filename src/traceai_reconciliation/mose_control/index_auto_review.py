"""Load MOSE documentary exceptions from a VERIFIED existing local source index.

No hidden raw data in repo. No WMS/NT match claim; these findings require review.
"""
from __future__ import annotations
from pathlib import Path
from contextlib import closing
import sqlite3
from typing import Any

from .mose_source_index import MOSESQLiteSourceIndex
from .cross_warehouse_invoice import cross_warehouse_invoice_exits
from .review_queue import build_mose_review_queue


def create_review_cases_from_existing_index(
    *, cache_dir: str | Path, wms_path: str | Path,
    wme_path: str | Path, production_path: str | Path | None = None,
    max_invoices: int = 20000,
) -> dict[str, Any]:
    """Generate review cases only when the source index matches raw file hashes.

    Does not rebuild indexes, to avoid surprising long-running jobs from UI.
    A separate standard TraceAI indexing step must prepare the database first.
    """
    if not 1 <= max_invoices <= 20000:
        raise ValueError("max_invoices must be between 1 and 20000")
    if not all(Path(p).is_file() for p in (wms_path, wme_path)):
        return {"status": "SOURCE_FILES_MISSING", "cases": [], "verdict": "REVIEW"}
    index = MOSESQLiteSourceIndex(cache_dir)
    if not index.is_current(wms_path, wme_path):
        return {"status": "SOURCE_INDEX_MISSING_OR_STALE", "cases": [], "verdict": "REVIEW"}
    # Read F rows belonging to MOSE user OR MOSE warehouse; include companion
    # lines from other warehouses on the same invoice, keyed by doc/date.
    connection = sqlite3.connect(f"file:{index.db_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        with closing(connection):
            keys = connection.execute(
                """SELECT DISTINCT TRIM(CAST(Document AS TEXT)), TRIM(CAST(Date AS TEXT))
                   FROM wme WHERE UPPER(TRIM(CAST(OperationType AS TEXT))) = 'F'
                   AND (UPPER(TRIM(CAST(Note AS TEXT))) = 'MOSE'
                        OR UPPER(TRIM(CAST(Warehouse AS TEXT))) = 'MOSE')
                   LIMIT ?""", (max_invoices + 1,),
            ).fetchall()
            if len(keys) > max_invoices:
                return {"status": "TOO_MANY_DOCUMENTS_REVIEW", "cases": [], "verdict": "REVIEW"}
            events = []
            for document, day in keys:
                rows = connection.execute(
                    """SELECT Document, Date, ProductName, Partner, Unit,
                              Warehouse, SignedQuantity, SourceRowNumber,
                              OperationType
                       FROM wme WHERE TRIM(CAST(Document AS TEXT)) = ?
                       AND TRIM(CAST(Date AS TEXT)) = ?
                       AND UPPER(TRIM(CAST(OperationType AS TEXT))) = 'F'""",
                    (document, day),
                )
                for doc, dt, product, partner, unit, warehouse, qty, source_row, op in rows:
                    events.append(dict(document=doc, date=dt, product_name=product,
                                       partner=partner, unit=unit, warehouse=warehouse,
                                       quantity=qty, source_row=source_row, operation_type=op))
    except sqlite3.Error as exc:
        return {"status": "SOURCE_QUERY_BLOCKED", "error_type": type(exc).__name__,
                "cases": [], "verdict": "REVIEW"}
    findings = cross_warehouse_invoice_exits(events)
    return {"status": "WME_CROSS_WAREHOUSE_SCREEN_REVIEW",
            "scanned_invoice_keys": len(keys), "findings": len(findings),
            "cases": build_mose_review_queue(findings), "verdict": "REVIEW",
            "limitations": "F multi-warehouse only; no WMS delivery proof, NT linking, stock balance or human acceptance."}

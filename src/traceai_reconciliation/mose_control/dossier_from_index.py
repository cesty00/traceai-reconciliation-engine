"""Build source-grounded MOSE dossier from a *current* local SQLite index.

Read-only. Supporting NT and WMS rows are explicitly candidates, never MATCH.
"""
from __future__ import annotations
from pathlib import Path
from contextlib import closing
import sqlite3
from typing import Any

from traceai_reconciliation.investigation.source_index import SQLiteSourceIndex
from .case_dossier import compose_mose_case


def dossier_from_current_index(*, case: dict[str, Any],
    cache_dir: str | Path, wms_path: str | Path, wme_path: str | Path,
    production_path: str | Path) -> dict[str, Any]:
    if not all(Path(p).is_file() for p in (wms_path, wme_path, production_path)):
        return {"status": "SOURCE_FILES_MISSING", "verdict": "REVIEW"}
    index = SQLiteSourceIndex(cache_dir)
    if not index.is_current(wms_path, wme_path, production_path):
        return {"status": "SOURCE_INDEX_MISSING_OR_STALE", "verdict": "REVIEW"}
    rows = case.get("evidence_source_rows")
    if (not isinstance(rows, list) or not rows
            or any(not isinstance(x, int) or isinstance(x, bool) or x < 1 for x in rows)):
        return {"status": "CASE_SOURCE_ROWS_MISSING", "verdict": "REVIEW"}
    if len(rows) > 100:
        return {"status": "CASE_TOO_LARGE", "verdict": "REVIEW"}
    path = index.db_path.resolve()
    try:
        with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as db:
            marks = ",".join("?" for _ in rows)
            invoices = db.execute(
                f"""SELECT Document, Date, ProductName, Warehouse, SignedQuantity,
                           SourceRowNumber, OperationType, Partner, Unit, Balance
                    FROM wme WHERE SourceRowNumber IN ({marks})
                    AND UPPER(TRIM(CAST(OperationType AS TEXT))) = 'F'""", rows).fetchall()
            if len(invoices) != len(rows):
                return {"status": "CASE_SOURCE_PROVENANCE_MISMATCH", "verdict": "REVIEW"}
            invoice_rows = [
                {"document": x[0], "date": x[1], "product_name": x[2],
                 "warehouse": x[3], "quantity": x[4], "source_row": x[5],
                 "operation_type": x[6], "partner": x[7], "unit": x[8]}
                for x in invoices
            ]
            names = sorted({str(x["product_name"]) for x in invoice_rows})
            nt = []
            for name in names:
                for x in db.execute(
                    """SELECT Document, Date, ProductName, Warehouse, SignedQuantity,
                              SourceRowNumber, OperationType FROM wme
                       WHERE ProductName=? AND UPPER(TRIM(OperationType))='NT'
                       ORDER BY SourceRowNumber DESC LIMIT 30""", (name,)):
                    nt.append(dict(zip(("document","date","product_name","warehouse",
                                        "quantity","source_row","operation_type"), x)))
            balances = [
                {"warehouse": x[3], "product_code": str(x[2]),
                 "balance": x[9], "source_row": x[5]}
                for x in invoices if x[9] is not None
            ]
    except sqlite3.Error:
        return {"status": "SOURCE_QUERY_BLOCKED", "verdict": "REVIEW"}
    return compose_mose_case(
        case_id=str(case.get("case_id") or ""), invoices_wme=invoice_rows,
        nt_wme_candidates=nt, observed_wme_balances=balances,
    )

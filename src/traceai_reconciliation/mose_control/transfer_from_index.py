"""Read-only extraction and three-leg screening of selected whole documents."""
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Any
from .transfer_three_leg_audit import screen_complete_mose_transfer


def screen_transfer_from_mose_index(db_path: str | Path, *,
                                    wms_document: str, wme_nt: str,
                                    max_rows: int = 10000) -> dict[str, Any]:
    if not wms_document.strip() or not str(wme_nt).strip() or not 1 <= max_rows <= 100000:
        return {"status": "INVALID_DOCUMENT_SELECTION_REVIEW", "verdict": "REVIEW"}
    try:
        with closing(sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)) as db:
            db.execute("PRAGMA query_only=ON")
            wms_columns = {x[1] for x in db.execute("PRAGMA table_info(wms)")}
            required = {"Numar comanda", "Denumire articol", "Cantitate", "SourceRowNumber"}
            if not required.issubset(wms_columns):
                return {"status": "WMS_SOURCE_COLUMNS_MISSING_REVIEW", "verdict": "REVIEW"}
            wms = db.execute(
                'SELECT "Denumire articol", "Cantitate", SourceRowNumber FROM wms '
                'WHERE TRIM(CAST("Numar comanda" AS TEXT))=? LIMIT ?',
                (wms_document, max_rows + 1)).fetchall()
            nt = db.execute(
                "SELECT ProductName, SignedQuantity, Warehouse, SourceRowNumber "
                "FROM wme WHERE UPPER(TRIM(CAST(OperationType AS TEXT)))='NT' "
                "AND TRIM(CAST(Document AS TEXT))=? LIMIT ?",
                (str(wme_nt), max_rows + 1)).fetchall()
    except (sqlite3.Error, OSError):
        return {"status": "TRANSFER_INDEX_QUERY_FAILED_REVIEW", "verdict": "REVIEW"}
    if len(wms) > max_rows or len(nt) > max_rows:
        return {"status": "TRANSFER_SOURCE_TRUNCATED_REVIEW", "verdict": "REVIEW"}
    wms_lines = [
        {"document": wms_document, "product_name": x[0],
         "quantity": x[1], "source_row": x[2]} for x in wms]
    outgoing, incoming, other = [], [], []
    for product, qty, warehouse, source_row in nt:
        row = {"document": str(wme_nt), "product_name": product,
               "quantity": qty, "source_row": source_row}
        normalized = str(warehouse or "").strip().upper()
        if normalized == "MOSE" and float(qty or 0) > 0:
            incoming.append(row)
        elif normalized in {"DEPOZIT PRINCIPAL", "DP"} and float(qty or 0) < 0:
            outgoing.append(row)
        else:
            other.append(source_row)
    if other:
        return {"status": "TRANSFER_NT_OTHER_WAREHOUSE_OR_SIGN_REVIEW",
                "unexpected_wme_source_rows": other, "verdict": "REVIEW"}
    return screen_complete_mose_transfer(wms_lines, outgoing, incoming)

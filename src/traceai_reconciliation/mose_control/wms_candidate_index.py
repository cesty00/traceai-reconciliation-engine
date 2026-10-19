"""Read-only WMS candidates for a MOSE invoice from an existing SQLite index.

Exact normalized product name is only a screening key. No document MATCH.
"""
from __future__ import annotations
from contextlib import closing
import sqlite3
from pathlib import Path
from typing import Any, Sequence


def screen_wms_invoice_candidates(db_path: str | Path, product_names: Sequence[str],
                                  *, limit_per_product: int = 100) -> dict[str, Any]:
    if not 1 <= limit_per_product <= 500:
        raise ValueError("Invalid candidate limit")
    allowed = {
        "product": ("Denumire articol", "DenumireArticol", "Denumire produs"),
        "operation": ("Tip operatiune", "Operatiune", "Tip operațiune"),
        "order": ("Numar comanda", "Numar Comanda", "Număr comandă"),
        "quantity": ("Cantitate",),
        "date": ("Data", "Data operatie", "Data operatiune"),
    }
    try:
        with closing(sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)) as db:
            db.execute("PRAGMA query_only=ON")
            columns = {r[1] for r in db.execute("PRAGMA table_info(wms)")}
            selected = {key: next((alias for alias in choices if alias in columns), None)
                        for key, choices in allowed.items()}
            if any(value is None for value in selected.values()) or "SourceRowNumber" not in columns:
                return {"status": "WMS_COLUMNS_UNSUPPORTED_REVIEW", "candidates": [],
                        "missing": [key for key, value in selected.items() if value is None],
                        "verdict": "REVIEW"}
            def quoted(key: str) -> str:
                return '"' + selected[key].replace('"', '""') + '"'
            found = []
            truncated = False
            for name in sorted({str(x).strip() for x in product_names if str(x).strip()}):
                query = f"""SELECT {quoted('product')}, {quoted('operation')},
                               {quoted('order')}, {quoted('quantity')}, {quoted('date')},
                               SourceRowNumber FROM wms
                            WHERE UPPER(TRIM({quoted('product')}))=UPPER(TRIM(?))
                            AND UPPER(TRIM({quoted('operation')})) IN ('LIVRARE', 'DELIVERY')
                            ORDER BY SourceRowNumber DESC LIMIT ?"""
                rows = db.execute(query, (name, limit_per_product + 1)).fetchall()
                truncated = truncated or len(rows) > limit_per_product
                for product, operation, order, quantity, day, source_row in rows[:limit_per_product]:
                    order = str(order or "").strip()
                    found.append({
                        "product_name": product, "operation_type": operation,
                        "document": order, "order": order, "quantity": quantity,
                        "date": day, "source_row": source_row,
                        "candidate_class": (
                            "TRANSFER_MOSE" if order.upper().startswith("TRANSFER_MOSE")
                            else "DIRECT_DELIVERY_CANDIDATE"
                        ),
                    })
    except sqlite3.Error:
        return {"status": "WMS_QUERY_BLOCKED_REVIEW", "candidates": [], "verdict": "REVIEW"}
    return {"status": "WMS_CANDIDATES_REVIEW", "candidates": found,
            "truncated": truncated, "verdict": "REVIEW",
            "warning": "Candidate by product only, no invoice linkage or match."}

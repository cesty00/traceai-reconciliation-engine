"""Read-only WMS candidates for a MOSE invoice from an existing SQLite index.

Exact normalized product name is only a screening key. No document MATCH.
"""
from __future__ import annotations
from contextlib import closing
import sqlite3
from pathlib import Path
from typing import Any, Sequence
from datetime import date, datetime, timedelta


def screen_wms_invoice_candidates(db_path: str | Path, product_names: Sequence[str],
                                  *, invoice_date: str | None = None,
                                  invoice_partner: str | None = None,
                                  lookback_days: int = 30,
                                  limit_per_product: int = 100) -> dict[str, Any]:
    if lookback_days < 0 or lookback_days > 366:
        raise ValueError('Invalid lookback window')
    target = None
    if invoice_date is not None:
        try:
            target = date.fromisoformat(str(invoice_date)[:10])
        except ValueError as exc:
            raise ValueError('Invalid invoice date') from exc
    if not 1 <= limit_per_product <= 500:
        raise ValueError("Invalid candidate limit")
    allowed = {
        "product": ("Denumire articol", "DenumireArticol", "Denumire produs"),
        "operation": ("Tip operatiune", "Operatiune", "Tip operațiune"),
        "order": ("Numar comanda", "Numar Comanda", "Număr comandă"),
        "quantity": ("Cantitate",),
        "date": ("Data", "Data operatie", "Data operatiune"),
        "partner": ("Partener", "Client"),
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
                               {quoted('partner')}, SourceRowNumber FROM wms
                            WHERE UPPER(TRIM({quoted('product')}))=UPPER(TRIM(?))
                            AND UPPER(TRIM({quoted('operation')})) IN ('LIVRARE', 'DELIVERY')
                            ORDER BY SourceRowNumber DESC LIMIT ?"""
                # A source-row LIMIT before date screening may hide historical
                # candidates. Read all matching product deliveries, then bound.
                rows = db.execute(query.replace("ORDER BY SourceRowNumber DESC LIMIT ?", "ORDER BY SourceRowNumber DESC"), (name,)).fetchall()
                if target is not None:
                    filtered = []
                    for item in rows:
                        raw_day = str(item[4] or "").strip()
                        parsed = None
                        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
                            fragment = raw_day[:10] if fmt != "%m/%d/%Y" else raw_day.split(" ")[0]
                            try:
                                parsed = datetime.strptime(fragment, fmt).date()
                                break
                            except ValueError:
                                continue
                        if parsed is not None and target - timedelta(days=lookback_days) <= parsed <= target:
                            filtered.append(item)
                    rows = filtered
                truncated = truncated or len(rows) > limit_per_product
                for product, operation, order, quantity, day, partner, source_row in rows[:limit_per_product]:
                    order = str(order or "").strip()
                    is_transfer = order.upper().startswith("TRANSFER_MOSE") and str(partner or "").strip().upper() == "DP->MOSE"
                    internal_route = str(partner or "").strip().upper() == "DP->MOSE"
                    normalized_partner = " ".join(str(partner or "").upper().replace("-SEDIU FIRMA", "").replace("S.R.L.", "SRL").split())
                    expected_partner = " ".join(str(invoice_partner or "").upper().replace("-SEDIU FIRMA", "").replace("S.R.L.", "SRL").split())
                    found.append({
                        "product_name": product, "operation_type": operation,
                        "document": order, "order": order, "quantity": quantity,
                        "date": day, "source_row": source_row, "partner": partner,
                        "partner_screen": ("NOT_APPLICABLE_TRANSFER" if internal_route else
                            "PARTNER_CANDIDATE" if expected_partner and normalized_partner == expected_partner else
                            "DIFFERENT_OR_UNVERIFIED_PARTNER"),
                        "candidate_class": (
                            "TRANSFER_MOSE" if is_transfer
                            else "INTERNAL_ROUTE_REVIEW" if internal_route or order.upper().startswith("TRANSFER_MOSE")
                            else "DIRECT_DELIVERY_CANDIDATE"
                        ),
                    })
    except sqlite3.Error:
        return {"status": "WMS_QUERY_BLOCKED_REVIEW", "candidates": [], "verdict": "REVIEW"}
    return {"status": "WMS_CANDIDATES_REVIEW", "candidates": found,
            "truncated": truncated, "verdict": "REVIEW",
            "warning": "Candidate by product and optional date range only; no invoice linkage or match."}

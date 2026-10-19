"""Build source-grounded MOSE dossier from a *current* local SQLite index.

Read-only. Supporting NT and WMS rows are explicitly candidates, never MATCH.
"""
from __future__ import annotations
from pathlib import Path
from contextlib import closing
import sqlite3
from typing import Any

from .mose_source_index import MOSESQLiteSourceIndex
from .case_dossier import compose_mose_case
from .wms_candidate_index import screen_wms_invoice_candidates
from .invoice_balance_evidence import invoice_balance_evidence
from .reference_acceptance import audit_f91655_dossier
from .generic_evidence_audit import audit_mose_document_evidence
from .quantity_candidate_audit import screen_invoice_delivery_quantities
from .document_link_audit import screen_delivery_document_links


def dossier_from_current_index(*, case: dict[str, Any],
    cache_dir: str | Path, wms_path: str | Path, wme_path: str | Path,
    production_path: str | Path | None = None) -> dict[str, Any]:
    if not all(Path(p).is_file() for p in (wms_path, wme_path)):
        return {"status": "SOURCE_FILES_MISSING", "verdict": "REVIEW"}
    index = MOSESQLiteSourceIndex(cache_dir)
    if not index.is_mose_current(wms_path, wme_path):
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
                 "operation_type": x[6], "partner": x[7], "unit": x[8],
                 "reported_balance": x[9]}
                for x in invoices
            ]
            names = sorted({str(x["product_name"]) for x in invoice_rows})
            from datetime import datetime, timedelta
            def parse_day(value):
                raw = str(value or "").strip()
                for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                    try:
                        return datetime.strptime(raw[:10], fmt).date()
                    except ValueError:
                        continue
                return None
            days = {parse_day(x["date"]) for x in invoice_rows}
            if len(days) != 1 or None in days:
                return {"status": "INVOICE_DATE_AMBIGUITY_REVIEW", "verdict": "REVIEW"}
            invoice_day = next(iter(days))
            cutoff = invoice_day - timedelta(days=30)
            nt = []
            nt_truncated = False
            for name in names:
                rows = db.execute(
                    """SELECT Document, Date, ProductName, Warehouse, SignedQuantity,
                              SourceRowNumber, OperationType FROM wme
                       WHERE ProductName=? AND UPPER(TRIM(OperationType))='NT'
                       ORDER BY SourceRowNumber DESC""", (name,)).fetchall()
                valid = [x for x in rows if (parse_day(x[1]) is not None
                         and cutoff <= parse_day(x[1]) <= invoice_day)]
                nt_truncated = nt_truncated or len(valid) > 60
                for x in valid[:60]:
                    nt.append(dict(zip(("document","date","product_name","warehouse",
                                        "quantity","source_row","operation_type"), x)))
            balances = [
                {"warehouse": x[3], "product_code": str(x[2]),
                 "balance": x[9], "source_row": x[5]}
                for x in invoices if x[9] is not None
            ]
    except sqlite3.Error:
        return {"status": "SOURCE_QUERY_BLOCKED", "verdict": "REVIEW"}
    wms_screen = screen_wms_invoice_candidates(path, names, invoice_date=invoice_day.isoformat(), invoice_partner=invoice_rows[0]['partner'])
    if wms_screen['status'] != 'WMS_CANDIDATES_REVIEW':
        return {'status': wms_screen['status'], 'verdict': 'REVIEW',
                'wms_screen': wms_screen}
    transfers = [x for x in wms_screen['candidates'] if x['candidate_class'] == 'TRANSFER_MOSE']
    deliveries = [x for x in wms_screen['candidates'] if x['candidate_class'] != 'TRANSFER_MOSE']
    dossier = compose_mose_case(
        case_id=str(case.get("case_id") or ""), invoices_wme=invoice_rows,
        nt_wme_candidates=nt, observed_wme_balances=balances,
        transfers_wms_candidates=transfers, delivery_wms_candidates=deliveries,
    )
    if dossier.get('status') == 'AWAITING_OPERATOR_DOCUMENT_CHECK':
        dossier['wms_candidate_screen_truncated'] = wms_screen['truncated']
        dossier['nt_candidate_screen_truncated'] = nt_truncated
        dossier['invoice_balance_evidence'] = invoice_balance_evidence(invoice_rows)
        dossier['generic_evidence_audit'] = audit_mose_document_evidence(dossier)
        dossier['document_link_audit'] = screen_delivery_document_links(
            dossier['wme_invoices_source_evidence'], wms_screen['candidates'])
        dossier['quantity_candidate_audit'] = screen_invoice_delivery_quantities(
            dossier['wme_invoices_source_evidence'], wms_screen['candidates'],
            candidates_truncated=wms_screen['truncated'])
        if str(dossier.get('invoice_document')) == '91655':
            dossier['reference_acceptance'] = audit_f91655_dossier(dossier)
    return dossier

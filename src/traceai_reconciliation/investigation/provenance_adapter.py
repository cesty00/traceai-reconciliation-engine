"""Read-only source provenance for one supported supplier receipt family.

This module does not authorize MATCH, confirmed economic impact, or stock edits.
It is intentionally not integrated with engine.py or report generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal
import sqlite3

import pandas as pd

from .source_index import SQLiteSourceIndex

Status = Literal["COMPLETE", "UNAVAILABLE"]


@dataclass(frozen=True, slots=True)
class SourceCoordinate:
    system: Literal["WMS", "WME"]
    source_sha256: str
    physical_row_number: int


@dataclass(frozen=True, slots=True)
class ReceiptProvenance:
    status: Status
    reason: str
    source_lines: tuple[SourceCoordinate, ...] = ()


def _unavailable(reason: str) -> ReceiptProvenance:
    return ReceiptProvenance("UNAVAILABLE", reason)


def resolve_supplier_receipt_provenance(
    index: SQLiteSourceIndex,
    *,
    wms_path: str | Path,
    wme_path: str | Path,
    production_path: str | Path,
    product_code: str,
    product_name: str,
    document: str,
) -> ReceiptProvenance:
    """Resolve an exact synthetic/real candidate row set, never economic ownership.

    Only WMS IN... Receptie -> WME FE for one exact product/document is
    supported. Unsupported/ambiguous source data fails closed to UNAVAILABLE.
    """
    wms_path, wme_path, production_path = map(
        Path, (wms_path, wme_path, production_path)
    )
    if not product_code or not product_name or not document:
        return _unavailable("IDENTITY_MISSING")
    if not index.is_current(wms_path, wme_path, production_path):
        return _unavailable("STALE_SOURCE_INDEX")
    hashes = {
        "WMS": sha256(wms_path.read_bytes()).hexdigest(),
        "WME": sha256(wme_path.read_bytes()).hexdigest(),
    }
    with sqlite3.connect(index.db_path) as db:
        meta = dict(db.execute("SELECT source_key,sha256 FROM _source_meta"))
        if meta.get("wms") != hashes["WMS"] or meta.get("wme") != hashes["WME"]:
            return _unavailable("SOURCE_HASH_MISMATCH")
        # A document reused by another product must never inherit a claim.
        wme_foreign = db.execute(
            'SELECT COUNT(*) FROM wme WHERE CAST(Document AS TEXT) = ? '
            "AND UPPER(TRIM(CAST(OperationType AS TEXT))) = 'FE' "
            "AND TRIM(CAST(ProductName AS TEXT)) != ?",
            (document, product_name),
        ).fetchone()[0]
        wms_foreign = db.execute(
            'SELECT COUNT(*) FROM wms WHERE TRIM(CAST("Document intrare" AS TEXT)) = ? '
            'AND TRIM(CAST("Cod articol" AS TEXT)) != ?',
            (document, product_code),
        ).fetchone()[0]
        if wme_foreign or wms_foreign:
            return _unavailable("DOCUMENT_REUSED_ACROSS_PRODUCTS")
    wms_rows = index.read_wms_product(product_code)
    wme_rows, _ = index.read_wme_product(product_name)
    wms_cols = {"SourceRowNumber", "Document intrare", "Cantitate",
                "Numar comanda", "Tip operatiune"}
    wme_cols = {"SourceRowNumber", "Document", "SignedQuantity",
                "OperationType"}
    if not wms_cols.issubset(wms_rows.columns) or not wme_cols.issubset(wme_rows.columns):
        return _unavailable("REQUIRED_COLUMNS_MISSING")
    wms = wms_rows[
        wms_rows["Document intrare"].astype(str).str.strip().eq(document)
    ]
    wme = wme_rows[wme_rows["Document"].astype(str).str.strip().eq(document)]
    if wms.empty or wme.empty:
        return _unavailable("SOURCE_SET_INCOMPLETE")
    if not (wms["Tip operatiune"].astype(str).str.strip().eq("Receptie").all()
            and wms["Numar comanda"].astype(str).str.strip().str.upper().str.startswith("IN").all()
            and wme["OperationType"].astype(str).str.strip().str.upper().eq("FE").all()):
        return _unavailable("UNSUPPORTED_DOCUMENT_FAMILY")
    qty_wms = pd.to_numeric(wms["Cantitate"], errors="coerce")
    qty_wme = pd.to_numeric(wme["SignedQuantity"], errors="coerce")
    if (qty_wms.isna().any() or qty_wme.isna().any()
            or (qty_wms <= 0).any() or (qty_wme <= 0).any()
            or abs(float(qty_wms.sum()) - float(qty_wme.sum())) > 0.001):
        return _unavailable("QUANTITY_UNVERIFIED")
    lines = []
    for system, rows in (("WMS", wms), ("WME", wme)):
        for value in rows["SourceRowNumber"]:
            try:
                number = int(value)
                if number < 2 or float(value) != number:
                    raise ValueError
            except (TypeError, ValueError, OverflowError):
                return _unavailable("SOURCE_COORDINATES_INVALID")
            lines.append(SourceCoordinate(system, hashes[system], number))
    if len(lines) != len(set(lines)):
        return _unavailable("DUPLICATE_SOURCE_IDENTITY")
    # Recheck after all reads to reject any intervening source replacement.
    if not index.is_current(wms_path, wme_path, production_path):
        return _unavailable("STALE_SOURCE_INDEX")
    return ReceiptProvenance(
        "COMPLETE", "SOURCE_ROWS_IDENTIFIED", tuple(sorted(
            lines, key=lambda line: (line.system, line.physical_row_number)
        ))
    )

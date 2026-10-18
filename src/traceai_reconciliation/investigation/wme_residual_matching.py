from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class WmeResidualMovementResult:
    residual_movements: list[dict[str, Any]]
    wme_signed_total: float
    system_difference_effect: float


def confirmed_inbound_wme_indexes(
    wme_rows: pd.DataFrame,
    receipt_documents: list[dict[str, Any]],
    tolerance: float = 0.001,
) -> set[object]:
    """Exclude only exact, quantity-supported inbound source rows.

    A document-level MATCH must be consistent with actual WME rows before its
    FE/F fallback may be omitted from the residual classifier. Other entries,
    including ambiguous document/type families, stay visible for REVIEW.
    """
    from .receipt_matching import _document_number

    if wme_rows.empty or not {"OperationType", "Document", "SignedQuantity"}.issubset(wme_rows.columns):
        return set()
    work = wme_rows.copy()
    work["_receipt_type"] = work["OperationType"].astype(str).str.strip().str.upper()
    work["_receipt_doc"] = work["Document"].map(_document_number)
    work["_receipt_qty"] = pd.to_numeric(work["SignedQuantity"], errors="coerce").fillna(0.0)
    excluded: set[object] = set()
    for match in receipt_documents:
        if match.get("status") != "MATCH":
            continue
        doc = _document_number(match.get("document"))
        op = str(match.get("wme_operation_type") or "").strip().upper()
        if not doc or op not in {"FE", "F", "NT"}:
            continue
        rows = work[
            work["_receipt_doc"].eq(doc)
            & work["_receipt_type"].eq(op)
            & work["_receipt_qty"].gt(0)
        ]
        if rows.empty:
            continue
        if abs(float(rows["_receipt_qty"].sum()) - float(match.get("wme_quantity") or 0)) <= tolerance:
            excluded.update(rows.index.tolist())
    return excluded


def match_wme_residual_movements(
    wme_rows: pd.DataFrame,
    excluded_warehouses: set[str] | None = None,
    excluded_indexes: set[object] | None = None,
) -> WmeResidualMovementResult:
    """
    Identify WME stock-affecting rows outside the standard operational set.

    Standard types handled elsewhere:
    AE, NP, BC, NT and StocInitial.

    The result reports evidence only. A positive WME-only movement contributes
    negatively to WMS-WME difference, hence system_difference_effect = -WME net.
    """
    if wme_rows.empty:
        return WmeResidualMovementResult([], 0.0, 0.0)

    required = {"OperationType", "SignedQuantity", "Warehouse"}
    if not required.issubset(wme_rows.columns):
        return WmeResidualMovementResult([], 0.0, 0.0)

    standard_types = {"AE", "NP", "BC", "NT", "STOCINITIAL"}
    excluded = {
        str(value).strip().upper()
        for value in (excluded_warehouses or set())
    }

    work = wme_rows.copy()
    if excluded_indexes:
        work = work.loc[~work.index.isin(excluded_indexes)].copy()
    work["_type"] = (
        work["OperationType"].astype(str).str.strip().str.upper()
    )
    work["_warehouse"] = (
        work["Warehouse"].astype(str).str.strip().str.upper()
    )
    work["_qty"] = pd.to_numeric(
        work["SignedQuantity"], errors="coerce"
    ).fillna(0.0)

    residual = work[
        ~work["_type"].isin(standard_types)
        & ~work["_warehouse"].isin(excluded)
        & work["_qty"].ne(0)
    ].copy()

    movements: list[dict[str, Any]] = []
    if not residual.empty:
        group_cols = ["_type", "Document", "_warehouse"]
        grouped = (
            residual.groupby(group_cols, dropna=False)["_qty"]
            .sum()
            .reset_index()
        )
        for _, row in grouped.iterrows():
            qty = float(row["_qty"])
            if abs(qty) <= 0.001:
                continue
            movements.append(
                {
                    "operation_type": str(row["_type"]),
                    "document": str(row["Document"]),
                    "warehouse": str(row["_warehouse"]),
                    "wme_signed_quantity": qty,
                    "system_difference_effect": -qty,
                    "status": "WME_ONLY_REVIEW",
                }
            )

    wme_signed_total = float(
        sum(item["wme_signed_quantity"] for item in movements)
    )
    return WmeResidualMovementResult(
        residual_movements=movements,
        wme_signed_total=wme_signed_total,
        system_difference_effect=-wme_signed_total,
    )

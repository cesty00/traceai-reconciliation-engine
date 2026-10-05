from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class GenericStockCorrectionResult:
    residual_corrections: list[dict[str, Any]]
    residual_total: float


def match_generic_wms_stock_corrections(
    wms_rows: pd.DataFrame,
    excluded_locations: set[str] | None = None,
) -> GenericStockCorrectionResult:
    """
    Identify WMS COR STOC negative adjustments without document that are not
    already in production locations or configured special-status locations.

    This is a conservative residual detector. It does not infer a WME document
    and never authorizes an adjustment.
    """
    if wms_rows.empty:
        return GenericStockCorrectionResult([], 0.0)

    required = {
        "Tip operatiune",
        "Cantitate",
        "Cod-motiv",
        "Locatie sursa",
    }
    missing = required - set(wms_rows.columns)
    if missing:
        return GenericStockCorrectionResult([], 0.0)

    work = wms_rows.copy()
    work["_op"] = work["Tip operatiune"].astype(str).str.strip()
    work["_reason"] = work["Cod-motiv"].astype(str).str.strip().str.upper()
    work["_location"] = work["Locatie sursa"].astype(str).str.strip()
    work["_qty"] = pd.to_numeric(
        work["Cantitate"], errors="coerce"
    ).fillna(0.0)

    if "Numar comanda" in work.columns:
        work["_document"] = (
            work["Numar comanda"].fillna("").astype(str).str.strip()
        )
    else:
        work["_document"] = ""

    production_locations: set[str] = set()
    if "Cod-motiv" in work.columns:
        production_out = work[
            work["_op"].eq("Ajustare pozitiva")
            & work["_reason"].eq("PRODUCTION-OUT")
        ]
        production_locations = {
            str(value).strip()
            for value in production_out["_location"].tolist()
            if str(value).strip()
        }

    excluded = {str(value).strip() for value in (excluded_locations or set())}
    excluded |= production_locations

    residual = work[
        work["_op"].eq("Ajustare negativa")
        & work["_reason"].eq("COR STOC")
        & work["_qty"].lt(0)
        & work["_document"].eq("")
        & ~work["_location"].isin(excluded)
    ].copy()

    corrections: list[dict[str, Any]] = []
    for _, row in residual.iterrows():
        corrections.append(
            {
                "date": row.get("Data", "-"),
                "quantity": float(row["_qty"]),
                "location": row["_location"],
                "lot": row.get("Lot", "-"),
                "document": "",
                "reason": (
                    "COR STOC WMS fără document, în afara locațiilor de "
                    "producție și a fluxurilor speciale deja tratate"
                ),
                "status": "WMS_ONLY_REVIEW",
            }
        )

    return GenericStockCorrectionResult(
        residual_corrections=corrections,
        residual_total=float(
            sum(item["quantity"] for item in corrections)
        ),
    )

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .production_matching import normalize_document


@dataclass(slots=True)
class ProductionInputMatchResult:
    documents: list[dict[str, Any]]
    residual_documents: list[dict[str, Any]]
    wms_total: float
    wme_bc_total: float
    residual_total: float


def match_production_inputs(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    tolerance: float = 0.001,
) -> ProductionInputMatchResult:
    """
    Compare WMS PRODUCTION-IN negative adjustments with WME BC by normalized
    production order and aggregate quantity.

    Matching is evidentiary only. It never authorizes stock correction.
    """
    if wms_rows.empty:
        return ProductionInputMatchResult([], [], 0.0, 0.0, 0.0)

    required = {"Tip operatiune", "Cantitate"}
    missing = required - set(wms_rows.columns)
    if missing:
        raise ValueError(
            f"WMS production-input matching: coloane lipsă {sorted(missing)}"
        )

    if "Cod-motiv" not in wms_rows.columns:
        return ProductionInputMatchResult([], [], 0.0, 0.0, 0.0)

    reason = wms_rows["Cod-motiv"].astype(str).str.strip().str.upper()
    pin_mask = (
        wms_rows["Tip operatiune"].astype(str).str.strip().eq("Ajustare negativa")
        & reason.eq("PRODUCTION-IN")
    )
    if not pin_mask.any():
        return ProductionInputMatchResult([], [], 0.0, 0.0, 0.0)

    if "Numar comanda" not in wms_rows.columns:
        raise ValueError(
            "WMS production-input matching: există PRODUCTION-IN, "
            "dar coloana 'Numar comanda' lipsește."
        )

    wms = wms_rows.loc[pin_mask].copy()
    wms["_doc"] = wms["Numar comanda"].map(normalize_document)
    wms["_qty"] = pd.to_numeric(
        wms["Cantitate"], errors="coerce"
    ).fillna(0.0)

    op_series = wme_rows.get(
        "OperationType",
        pd.Series(index=wme_rows.index, dtype=object),
    )
    bc = wme_rows[
        op_series.astype(str).str.strip().str.upper().eq("BC")
    ].copy()
    if not bc.empty:
        bc["_doc"] = bc["Document"].map(normalize_document)
        bc["_qty"] = pd.to_numeric(
            bc["SignedQuantity"], errors="coerce"
        ).fillna(0.0)
    else:
        bc["_doc"] = pd.Series(dtype=str)
        bc["_qty"] = pd.Series(dtype=float)

    wms_by_doc = (
        wms[wms["_doc"].ne("")]
        .groupby("_doc")["_qty"]
        .sum()
        .rename("wms_production_in")
    )
    wme_by_doc = (
        bc[bc["_doc"].ne("")]
        .groupby("_doc")["_qty"]
        .sum()
        .rename("wme_bc")
    )

    comparison = pd.concat(
        [wms_by_doc, wme_by_doc],
        axis=1,
    ).fillna(0.0)
    comparison["difference"] = (
        comparison["wms_production_in"] - comparison["wme_bc"]
    )

    documents: list[dict[str, Any]] = []
    residual_documents: list[dict[str, Any]] = []
    for doc, row in comparison.sort_index().iterrows():
        difference = float(row["difference"])
        item = {
            "document": str(doc),
            "wms_production_in": float(row["wms_production_in"]),
            "wme_bc": float(row["wme_bc"]),
            "difference": difference,
            "status": "MATCH" if abs(difference) <= tolerance else "QTY_DIFF",
        }
        documents.append(item)
        if abs(difference) > tolerance:
            residual_documents.append(item)

    return ProductionInputMatchResult(
        documents=documents,
        residual_documents=residual_documents,
        wms_total=float(comparison["wms_production_in"].sum()),
        wme_bc_total=float(comparison["wme_bc"].sum()),
        residual_total=float(comparison["difference"].sum()),
    )

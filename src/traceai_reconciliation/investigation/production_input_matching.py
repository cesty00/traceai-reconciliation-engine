from __future__ import annotations

from dataclasses import dataclass
import re
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
    reversed_documents: list[dict[str, Any]] | None = None
    wms_reversal_total: float = 0.0
    wms_effective_total: float = 0.0


def match_production_inputs(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    tolerance: float = 0.001,
    production_rows: pd.DataFrame | None = None,
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

    correction_by_doc: dict[str, float] = {}
    if {"Detalii", "Cod-motiv"}.issubset(wms_rows.columns):
        all_reason = (
            wms_rows["Cod-motiv"].astype(str).str.strip().str.upper()
        )
        all_operation = (
            wms_rows["Tip operatiune"].astype(str).str.strip()
        )
        all_quantity = pd.to_numeric(
            wms_rows["Cantitate"],
            errors="coerce",
        ).fillna(0.0)
        corrections = wms_rows[
            all_reason.eq("COR STOC")
            & all_operation.eq("Ajustare pozitiva")
            & all_quantity.gt(tolerance)
        ].copy()
        if not corrections.empty:
            corrections["_qty"] = pd.to_numeric(
                corrections["Cantitate"],
                errors="coerce",
            ).fillna(0.0)
            details = corrections["Detalii"].fillna("").astype(str)
            for doc in wms_by_doc.index:
                pattern = rf"(?<!\\d){re.escape(str(doc))}(?!\\d)"
                referenced = corrections[
                    details.str.contains(
                        pattern,
                        case=False,
                        regex=True,
                        na=False,
                    )
                ]
                if not referenced.empty:
                    correction_by_doc[str(doc)] = float(
                        referenced["_qty"].sum()
                    )

    comparison = pd.concat(
        [wms_by_doc, wme_by_doc],
        axis=1,
    ).fillna(0.0)
    comparison["wms_reversal"] = pd.Series(
        correction_by_doc,
        dtype=float,
    ).reindex(comparison.index).fillna(0.0)
    comparison["wms_effective"] = (
        comparison["wms_production_in"]
        + comparison["wms_reversal"]
    )
    comparison["difference"] = (
        comparison["wms_effective"] - comparison["wme_bc"]
    )

    production_by_doc: dict[str, float] = {}
    if production_rows is not None and not production_rows.empty:
        production = production_rows.copy()
        if {"TipLinie", "Numar Comanda", "CON_Cantitate Consumata"}.issubset(
            production.columns
        ):
            production = production[
                production["TipLinie"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq("CONSUM")
            ].copy()
            production["_doc"] = production["Numar Comanda"].map(
                normalize_document
            )
            production["_qty"] = pd.to_numeric(
                production["CON_Cantitate Consumata"],
                errors="coerce",
            ).fillna(0.0)
            production_by_doc = (
                production[production["_doc"].ne("")]
                .groupby("_doc")["_qty"]
                .sum()
                .to_dict()
            )

    documents: list[dict[str, Any]] = []
    residual_documents: list[dict[str, Any]] = []
    reversed_documents: list[dict[str, Any]] = []
    for doc, row in comparison.sort_index().iterrows():
        difference = float(row["difference"])
        wms_quantity = float(row["wms_production_in"])
        wms_reversal = float(row["wms_reversal"])
        wms_effective = float(row["wms_effective"])
        wme_quantity = float(row["wme_bc"])
        production_quantity = float(production_by_doc.get(str(doc), 0.0))
        production_confirmed = (
            production_quantity > tolerance
            and abs(abs(wms_quantity) - production_quantity) <= tolerance
        )
        fully_reversed = (
            wms_reversal > tolerance
            and abs(wms_effective) <= tolerance
        )

        if fully_reversed and abs(wme_quantity) <= tolerance:
            residual_kind = "WMS_PRODUCTION_IN_REVERSED"
            status = "REVERSED"
        elif fully_reversed:
            residual_kind = "WME_BC_PRESENT_AFTER_WMS_REVERSAL"
            status = "QTY_DIFF"
        elif (
            wms_reversal > tolerance
            and abs(wme_quantity) <= tolerance
        ):
            residual_kind = "WMS_PARTIAL_REVERSAL_BC_MISSING"
            status = "QTY_DIFF"
        elif abs(difference) <= tolerance:
            residual_kind = "MATCH"
            status = "MATCH"
        elif abs(wme_quantity) <= tolerance and abs(wms_effective) > tolerance:
            residual_kind = "WME_BC_MISSING"
            status = "QTY_DIFF"
        else:
            residual_kind = "WME_BC_QTY_DIFF"
            status = "QTY_DIFF"

        item = {
            "document": str(doc),
            "wms_production_in": wms_quantity,
            "wms_reversal": wms_reversal,
            "wms_effective": wms_effective,
            "wme_bc": wme_quantity,
            "production_consumption": production_quantity,
            "production_confirmed": production_confirmed,
            "fully_reversed": fully_reversed,
            "residual_kind": residual_kind,
            "difference": difference,
            "status": status,
        }
        documents.append(item)
        if fully_reversed and abs(wme_quantity) <= tolerance:
            reversed_documents.append(item)
        elif abs(difference) > tolerance:
            residual_documents.append(item)

    return ProductionInputMatchResult(
        documents=documents,
        residual_documents=residual_documents,
        wms_total=float(comparison["wms_production_in"].sum()),
        wme_bc_total=float(comparison["wme_bc"].sum()),
        residual_total=float(comparison["difference"].sum()),
        reversed_documents=reversed_documents,
        wms_reversal_total=float(comparison["wms_reversal"].sum()),
        wms_effective_total=float(comparison["wms_effective"].sum()),
    )

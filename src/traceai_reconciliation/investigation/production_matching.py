from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(slots=True)
class ProductionMatchResult:
    matched_documents: list[dict[str, Any]]
    reversal_pairs: list[dict[str, Any]]
    residual_wms_adjustments: list[dict[str, Any]]
    wms_positive_total: float
    wme_np_total: float
    residual_total: float
    document_residuals: list[dict[str, Any]] = field(default_factory=list)
    document_residual_total: float = 0.0


def normalize_document(value: object) -> str:
    """Normalize production/order document numbers for WMS-WME comparison."""
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""

    base = text.split("_", 1)[0]
    base = re.sub(r"^[A-Z]+", "", base)
    digits = re.sub(r"\D", "", base)
    if digits:
        return str(int(digits))
    return base


def _text(value: object) -> str:
    return "" if value is None or pd.isna(value) else str(value).strip()


def match_production_adjustments(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    tolerance: float = 0.001,
) -> ProductionMatchResult:
    """
    Reconcile WMS production output adjustments with WME NP.

    Safe rules:
    1. Compare WMS Ajustare pozitiva documents to WME NP by normalized
       document number and aggregate quantity.
    2. A WMS positive surplus can pair only with an unreferenced WMS negative
       adjustment on the same day, lot, production location and absolute row
       quantity. This exposes WMS correction/reversal pairs without hiding a
       positive quantity already represented in WME NP.
    3. Unreferenced negative adjustments in production locations remaining
       after those reversal pairs are returned as residual WMS adjustments.

    This function never authorizes stock/accounting correction.
    """
    if wms_rows.empty:
        return ProductionMatchResult([], [], [], 0.0, 0.0, 0.0)

    minimum_wms = {"Data", "Tip operatiune", "Cantitate"}
    missing_minimum = minimum_wms - set(wms_rows.columns)
    if missing_minimum:
        raise ValueError(
            f"WMS production matching: coloane de bază lipsă "
            f"{sorted(missing_minimum)}"
        )

    operation_values = (
        wms_rows["Tip operatiune"].astype(str).str.strip()
    )
    has_production_adjustment = operation_values.isin(
        ["Ajustare pozitiva", "Ajustare negativa"]
    ).any()
    if not has_production_adjustment:
        return ProductionMatchResult([], [], [], 0.0, 0.0, 0.0)

    production_columns = {"Numar comanda", "Locatie sursa", "Lot"}
    missing_production = production_columns - set(wms_rows.columns)
    if missing_production:
        raise ValueError(
            f"WMS production matching: operațiuni de ajustare existente, "
            f"dar coloane de producție lipsă {sorted(missing_production)}"
        )

    work = wms_rows.copy()
    work["Data"] = pd.to_datetime(work["Data"], errors="coerce", dayfirst=True)
    work["_qty"] = pd.to_numeric(work["Cantitate"], errors="coerce").fillna(0.0)
    work["_doc"] = work["Numar comanda"].map(normalize_document)
    work["_day"] = work["Data"].dt.date
    work["_location"] = work["Locatie sursa"].map(_text)
    work["_lot"] = work["Lot"].map(_text)

    positive_mask = (
        work["Tip operatiune"].astype(str).str.strip().eq("Ajustare pozitiva")
    )
    if "Cod-motiv" in work.columns:
        reason = work["Cod-motiv"].astype(str).str.strip().str.upper()
        production_out = reason.eq("PRODUCTION-OUT")
        if production_out.any():
            positive_mask &= production_out

    positives = work[positive_mask].copy()
    negatives = work[
        work["Tip operatiune"].astype(str).str.strip().eq("Ajustare negativa")
    ].copy()

    op_series = wme_rows.get(
        "OperationType",
        pd.Series(index=wme_rows.index, dtype=object),
    )
    wme_np = wme_rows[
        op_series.astype(str).str.strip().str.upper().eq("NP")
    ].copy()
    if not wme_np.empty:
        wme_np["_doc"] = wme_np["Document"].map(normalize_document)
        wme_np["_qty"] = pd.to_numeric(
            wme_np["SignedQuantity"], errors="coerce"
        ).fillna(0.0)
    else:
        wme_np["_doc"] = pd.Series(dtype=str)
        wme_np["_qty"] = pd.Series(dtype=float)

    wms_by_doc = (
        positives[positives["_doc"] != ""]
        .groupby("_doc", as_index=False)["_qty"]
        .sum()
        .rename(columns={"_qty": "wms_qty"})
    )
    wme_by_doc = (
        wme_np[wme_np["_doc"] != ""]
        .groupby("_doc", as_index=False)["_qty"]
        .sum()
        .rename(columns={"_qty": "wme_qty"})
    )
    comparison = (
        wms_by_doc.merge(wme_by_doc, on="_doc", how="outer")
        .fillna(0.0)
    )
    comparison["delta"] = comparison["wms_qty"] - comparison["wme_qty"]

    matched_documents: list[dict[str, Any]] = []
    surplus_docs: dict[str, float] = {}
    for _, row in comparison.iterrows():
        doc = str(row["_doc"])
        delta = float(row["delta"])
        matched_documents.append(
            {
                "document": doc,
                "wms_quantity": float(row["wms_qty"]),
                "wme_np_quantity": float(row["wme_qty"]),
                "difference": delta,
                "status": (
                    "MATCH" if abs(delta) <= tolerance else "QTY_DIFF"
                ),
            }
        )
        if delta > tolerance:
            surplus_docs[doc] = delta

    surplus_positive_rows: list[int] = []
    remaining_surplus = dict(surplus_docs)
    for idx, row in positives.sort_values("Data").iterrows():
        doc = row["_doc"]
        available = remaining_surplus.get(doc, 0.0)
        qty = float(row["_qty"])
        if available <= tolerance or qty <= tolerance:
            continue
        if qty <= available + tolerance:
            surplus_positive_rows.append(idx)
            remaining_surplus[doc] = max(0.0, available - qty)

    candidate_positive = positives.loc[surplus_positive_rows].copy()
    blank_negatives = negatives[
        negatives["_doc"].eq("") & negatives["_location"].ne("")
    ].copy()

    production_locations = set(
        positives["_location"].dropna().astype(str)
    )
    blank_negatives = blank_negatives[
        blank_negatives["_location"].isin(production_locations)
    ].copy()

    used_positive: set[int] = set()
    used_negative: set[int] = set()
    reversal_pairs: list[dict[str, Any]] = []

    for neg_idx, neg in blank_negatives.sort_values("Data").iterrows():
        neg_abs = abs(float(neg["_qty"]))
        candidates = candidate_positive[
            (~candidate_positive.index.isin(used_positive))
            & candidate_positive["_day"].eq(neg["_day"])
            & candidate_positive["_location"].eq(neg["_location"])
            & candidate_positive["_lot"].eq(neg["_lot"])
            & (
                candidate_positive["_qty"].sub(neg_abs).abs()
                <= tolerance
            )
        ]
        if candidates.empty:
            continue

        pos_idx = candidates.index[0]
        pos = candidates.loc[pos_idx]
        used_positive.add(pos_idx)
        used_negative.add(neg_idx)
        reversal_pairs.append(
            {
                "date": str(neg["Data"]),
                "location": neg["_location"],
                "lot": neg["_lot"],
                "quantity": neg_abs,
                "positive_document": pos["Numar comanda"],
                "positive_document_normalized": pos["_doc"],
                "positive_quantity": float(pos["_qty"]),
                "negative_quantity": float(neg["_qty"]),
                "status": "WMS_REVERSAL_PAIR",
            }
        )

    residual = blank_negatives[
        ~blank_negatives.index.isin(used_negative)
    ].copy()
    residual_wms_adjustments: list[dict[str, Any]] = []
    for _, row in residual.sort_values("Data").iterrows():
        residual_wms_adjustments.append(
            {
                "date": row["Data"],
                "operation_type": "Ajustare negativa",
                "quantity": float(row["_qty"]),
                "location": row["_location"],
                "lot": row["_lot"],
                "document": "",
                "reason": (
                    "Ajustare WMS fără document și fără pereche de "
                    "reversare identificată"
                ),
                "status": "WMS_ONLY_REVIEW",
            }
        )

    wms_positive_total = float(positives["_qty"].sum())
    wme_np_total = (
        float(wme_np["_qty"].sum()) if not wme_np.empty else 0.0
    )
    residual_total = float(
        sum(item["quantity"] for item in residual_wms_adjustments)
    )

    reversal_by_document: dict[str, float] = {}
    for item in reversal_pairs:
        document = str(item["positive_document_normalized"])
        reversal_by_document[document] = (
            reversal_by_document.get(document, 0.0)
            + float(item["quantity"])
        )

    document_residuals: list[dict[str, Any]] = []
    for item in matched_documents:
        document = str(item["document"])
        effective_difference = (
            float(item["difference"])
            - reversal_by_document.get(document, 0.0)
        )
        if abs(effective_difference) <= tolerance:
            continue
        document_residuals.append(
            {
                "document": document,
                "raw_difference": float(item["difference"]),
                "reversed_wms_positive": reversal_by_document.get(
                    document, 0.0
                ),
                "effective_difference": effective_difference,
                "status": "QTY_DIFF_AFTER_REVERSALS",
            }
        )

    document_residual_total = float(
        sum(item["effective_difference"] for item in document_residuals)
    )

    return ProductionMatchResult(
        matched_documents=matched_documents,
        reversal_pairs=reversal_pairs,
        residual_wms_adjustments=residual_wms_adjustments,
        wms_positive_total=wms_positive_total,
        wme_np_total=wme_np_total,
        residual_total=residual_total,
        document_residuals=document_residuals,
        document_residual_total=document_residual_total,
    )

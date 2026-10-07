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
    Reconcile WMS PRODUCTION-OUT with WME NP and deterministic WMS corrections.

    Conservative matching order:
    1. compare production documents WMS↔WME;
    2. apply COR STOC that explicitly references one production document;
    3. close WMS-only orders only when the signed COR STOC scope between that
       order and the next production order nets the order exactly;
    4. pair remaining WMS-only surplus rows by exact day/location/lot/quantity;
    5. attach a remaining negative COR STOC to an NP-backed order only when one
       unique production row matches day/location/lot/absolute quantity;
    6. keep every ambiguous/unconsumed correction as REVIEW.

    Technical orders whose production rows are all on lot TEST are excluded
    from the numeric explanation but remain visible in matched_documents.
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

    operation_values = wms_rows["Tip operatiune"].astype(str).str.strip()
    if not operation_values.isin(
        ["Ajustare pozitiva", "Ajustare negativa"]
    ).any():
        return ProductionMatchResult([], [], [], 0.0, 0.0, 0.0)

    production_columns = {"Numar comanda", "Locatie sursa", "Lot"}
    missing_production = production_columns - set(wms_rows.columns)
    if missing_production:
        raise ValueError(
            f"WMS production matching: operațiuni de ajustare existente, "
            f"dar coloane de producție lipsă {sorted(missing_production)}"
        )

    work = wms_rows.copy()
    work["Data"] = pd.to_datetime(
        work["Data"], errors="coerce", dayfirst=True
    )
    work["_qty"] = pd.to_numeric(
        work["Cantitate"], errors="coerce"
    ).fillna(0.0)
    work["_doc"] = work["Numar comanda"].map(normalize_document)
    work["_day"] = work["Data"].dt.date
    work["_location"] = work["Locatie sursa"].map(_text)
    work["_lot"] = work["Lot"].map(_text)
    work["_reason"] = (
        work.get(
            "Cod-motiv",
            pd.Series(index=work.index, dtype=object),
        )
        .map(_text)
        .str.upper()
    )
    work["_details"] = (
        work.get(
            "Detalii",
            pd.Series(index=work.index, dtype=object),
        )
        .map(_text)
    )

    positive_mask = work["Tip operatiune"].astype(str).str.strip().eq(
        "Ajustare pozitiva"
    )
    if work["_reason"].eq("PRODUCTION-OUT").any():
        positive_mask &= work["_reason"].eq("PRODUCTION-OUT")
    positives = work[positive_mask & work["_doc"].ne("")].copy()

    production_locations = {
        str(value).strip()
        for value in positives["_location"].dropna().tolist()
        if str(value).strip()
    }
    corrections = work[
        work["_reason"].eq("COR STOC")
        & work["_doc"].eq("")
        & work["_location"].isin(production_locations)
        & work["_qty"].abs().gt(tolerance)
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
        positives.groupby("_doc", as_index=False)["_qty"]
        .sum()
        .rename(columns={"_qty": "wms_qty"})
    )
    wme_by_doc = (
        wme_np[wme_np["_doc"].ne("")]
        .groupby("_doc", as_index=False)["_qty"]
        .sum()
        .rename(columns={"_qty": "wme_qty"})
    )
    comparison = (
        wms_by_doc.merge(wme_by_doc, on="_doc", how="outer")
        .fillna(0.0)
    )
    comparison["delta"] = comparison["wms_qty"] - comparison["wme_qty"]

    wms_qty_by_doc = {
        str(row["_doc"]): float(row["wms_qty"])
        for _, row in comparison.iterrows()
    }
    wme_qty_by_doc = {
        str(row["_doc"]): float(row["wme_qty"])
        for _, row in comparison.iterrows()
    }
    raw_delta_by_doc = {
        str(row["_doc"]): float(row["delta"])
        for _, row in comparison.iterrows()
    }

    test_documents: set[str] = set()
    for doc, group in positives.groupby("_doc"):
        lots = {
            _text(value).upper()
            for value in group["_lot"].tolist()
            if _text(value)
        }
        if lots and lots == {"TEST"}:
            test_documents.add(str(doc))

    matched_documents: list[dict[str, Any]] = []
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
                    "TEST_ORDER_IGNORED"
                    if doc in test_documents
                    else "MATCH"
                    if abs(delta) <= tolerance
                    else "QTY_DIFF"
                ),
            }
        )

    used_corrections: set[int] = set()
    used_positive: set[int] = set()
    reversal_pairs: list[dict[str, Any]] = []
    correction_effect_by_document: dict[str, float] = {}
    correction_evidence_by_document: dict[str, list[dict[str, Any]]] = {}

    # 1) Explicit document references in COR STOC details.
    known_docs = set(wms_qty_by_doc)
    production_reference_tokens = (
        "CORECTIE COMANDA",
        "CORECȚIE COMANDA",
        "PREDARE",
        "PRODUCTIE",
        "PRODUCȚIE",
        "COMANDA",
    )
    consumption_tokens = ("CONSUM", "MATERIE PRIMA", "MATERIE PRIMĂ")

    for corr_idx, corr in corrections.sort_values("Data").iterrows():
        details_upper = str(corr["_details"]).upper()
        if any(token in details_upper for token in consumption_tokens):
            continue
        if not any(
            token in details_upper for token in production_reference_tokens
        ):
            continue
        referenced = [
            doc
            for doc in known_docs
            if re.search(
                rf"(?<!\\d)0*{re.escape(str(doc))}(?!\\d)",
                details_upper,
            )
        ]
        if len(referenced) != 1:
            continue
        doc = referenced[0]
        effect = float(corr["_qty"])
        correction_effect_by_document[doc] = (
            correction_effect_by_document.get(doc, 0.0) + effect
        )
        correction_evidence_by_document.setdefault(doc, []).append(
            {
                "date": str(corr["Data"]),
                "quantity": effect,
                "lot": corr["_lot"],
                "details": corr["_details"],
                "status": "EXPLICIT_DOCUMENT_CORRECTION",
            }
        )
        used_corrections.add(corr_idx)

    # 2) Exact aggregate reversal of a WMS-only order inside its chronological
    # scope: from first production row until the next different production
    # document in the same location/day.
    wms_only_docs = [
        doc
        for doc in known_docs
        if wms_qty_by_doc.get(doc, 0.0) > tolerance
        and abs(wme_qty_by_doc.get(doc, 0.0)) <= tolerance
        and doc not in test_documents
    ]
    ordered_positives = positives.sort_values("Data")

    for doc in sorted(
        wms_only_docs,
        key=lambda value: (
            positives.loc[positives["_doc"].eq(value), "Data"].min()
        ),
    ):
        doc_rows = positives[positives["_doc"].eq(doc)].sort_values("Data")
        if doc_rows.empty:
            continue
        location_values = {
            value for value in doc_rows["_location"].tolist() if value
        }
        day_values = {
            value for value in doc_rows["_day"].tolist() if pd.notna(value)
        }
        if len(location_values) != 1 or len(day_values) != 1:
            continue
        location = next(iter(location_values))
        day = next(iter(day_values))
        start = doc_rows["Data"].min()
        end = doc_rows["Data"].max()

        next_other = ordered_positives[
            ordered_positives["_location"].eq(location)
            & ordered_positives["_day"].eq(day)
            & ordered_positives["Data"].gt(end)
            & ordered_positives["_doc"].ne(doc)
        ]["Data"]
        stop = next_other.min() if not next_other.empty else pd.NaT

        scope = corrections[
            (~corrections.index.isin(used_corrections))
            & corrections["_location"].eq(location)
            & corrections["_day"].eq(day)
            & corrections["Data"].ge(start)
        ].copy()
        if pd.notna(stop):
            scope = scope[scope["Data"].lt(stop)]
        if scope.empty:
            continue

        positive_total = float(doc_rows["_qty"].sum())
        correction_total = float(scope["_qty"].sum())
        if abs(positive_total + correction_total) > tolerance:
            continue

        for idx in doc_rows.index:
            used_positive.add(idx)
        for idx in scope.index:
            used_corrections.add(idx)

        reversal_pairs.append(
            {
                "date": str(scope["Data"].max()),
                "location": location,
                "lot": ",".join(
                    sorted(
                        {
                            value
                            for value in doc_rows["_lot"].tolist()
                            if value
                        }
                    )
                ),
                "quantity": positive_total,
                "positive_document": doc_rows.iloc[0]["Numar comanda"],
                "positive_document_normalized": doc,
                "positive_quantity": positive_total,
                "negative_quantity": correction_total,
                "status": "WMS_AGGREGATE_SCOPE_REVERSAL",
            }
        )

    # 3) Legacy exact row-level reversal fallback for remaining WMS surplus.
    reversal_by_document: dict[str, float] = {}
    for item in reversal_pairs:
        doc = str(item["positive_document_normalized"])
        reversal_by_document[doc] = (
            reversal_by_document.get(doc, 0.0)
            + float(item["quantity"])
        )

    remaining_surplus = {
        doc: max(
            0.0,
            raw_delta_by_doc.get(doc, 0.0)
            - reversal_by_document.get(doc, 0.0),
        )
        for doc in known_docs
        if raw_delta_by_doc.get(doc, 0.0) > tolerance
        and doc not in test_documents
    }
    candidate_positive_indices: list[int] = []
    for idx, row in ordered_positives.iterrows():
        if idx in used_positive:
            continue
        doc = str(row["_doc"])
        available = remaining_surplus.get(doc, 0.0)
        qty = float(row["_qty"])
        if available > tolerance and qty <= available + tolerance:
            candidate_positive_indices.append(idx)
            remaining_surplus[doc] = max(0.0, available - qty)

    candidate_positive = positives.loc[candidate_positive_indices].copy()
    remaining_negative = corrections[
        (~corrections.index.isin(used_corrections))
        & corrections["_qty"].lt(-tolerance)
    ].copy()

    for neg_idx, neg in remaining_negative.sort_values("Data").iterrows():
        neg_abs = abs(float(neg["_qty"]))
        candidates = candidate_positive[
            (~candidate_positive.index.isin(used_positive))
            & candidate_positive["_day"].eq(neg["_day"])
            & candidate_positive["_location"].eq(neg["_location"])
            & candidate_positive["_lot"].eq(neg["_lot"])
            & candidate_positive["_qty"].sub(neg_abs).abs().le(tolerance)
        ]
        if len(candidates) != 1:
            continue
        pos_idx = candidates.index[0]
        pos = candidates.loc[pos_idx]
        doc = str(pos["_doc"])
        used_positive.add(pos_idx)
        used_corrections.add(neg_idx)
        reversal_by_document[doc] = (
            reversal_by_document.get(doc, 0.0) + neg_abs
        )
        reversal_pairs.append(
            {
                "date": str(neg["Data"]),
                "location": neg["_location"],
                "lot": neg["_lot"],
                "quantity": neg_abs,
                "positive_document": pos["Numar comanda"],
                "positive_document_normalized": doc,
                "positive_quantity": float(pos["_qty"]),
                "negative_quantity": float(neg["_qty"]),
                "status": "WMS_REVERSAL_PAIR",
            }
        )

    # 4) Post-NP exact unreferenced correction. Only a unique positive row on
    # the same day/location/lot/absolute quantity may own the correction, and
    # the document must already be backed by NP with zero raw document delta.
    remaining_negative = corrections[
        (~corrections.index.isin(used_corrections))
        & corrections["_qty"].lt(-tolerance)
    ].copy()
    for corr_idx, corr in remaining_negative.sort_values("Data").iterrows():
        correction_abs = abs(float(corr["_qty"]))
        candidates = positives[
            positives["_day"].eq(corr["_day"])
            & positives["_location"].eq(corr["_location"])
            & positives["_lot"].eq(corr["_lot"])
            & positives["_qty"].sub(correction_abs).abs().le(tolerance)
        ].copy()
        candidates = candidates[
            candidates["_doc"].map(
                lambda doc: (
                    abs(wme_qty_by_doc.get(str(doc), 0.0)) > tolerance
                    and abs(raw_delta_by_doc.get(str(doc), 0.0)) <= tolerance
                    and str(doc) not in test_documents
                )
            )
        ]
        if len(candidates) != 1:
            continue
        pos = candidates.iloc[0]
        doc = str(pos["_doc"])
        effect = float(corr["_qty"])
        correction_effect_by_document[doc] = (
            correction_effect_by_document.get(doc, 0.0) + effect
        )
        correction_evidence_by_document.setdefault(doc, []).append(
            {
                "date": str(corr["Data"]),
                "quantity": effect,
                "lot": corr["_lot"],
                "details": corr["_details"],
                "status": "POST_NP_EXACT_ROW_CORRECTION",
            }
        )
        used_corrections.add(corr_idx)

    # Only still-unconsumed negative corrections remain operational REVIEW.
    residual = corrections[
        (~corrections.index.isin(used_corrections))
        & corrections["_qty"].lt(-tolerance)
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
                    "Ajustare WMS fără document și fără legătură univocă "
                    "de producție/reversare"
                ),
                "status": "WMS_ONLY_REVIEW",
                "cod_motiv": _text(row.get("Cod-motiv")),
                "details": _text(row.get("Detalii")),
            }
        )

    document_residuals: list[dict[str, Any]] = []
    for item in matched_documents:
        document = str(item["document"])
        if document in test_documents:
            continue
        raw_difference = float(item["difference"])
        reversed_amount = reversal_by_document.get(document, 0.0)
        correction_effect = correction_effect_by_document.get(document, 0.0)
        effective_difference = (
            raw_difference - reversed_amount + correction_effect
        )
        if abs(effective_difference) <= tolerance:
            continue
        document_residuals.append(
            {
                "document": document,
                "raw_difference": raw_difference,
                "reversed_wms_positive": reversed_amount,
                "correction_effect": correction_effect,
                "correction_evidence": correction_evidence_by_document.get(
                    document, []
                ),
                "effective_difference": effective_difference,
                "status": "QTY_DIFF_AFTER_REVERSALS_AND_CORRECTIONS",
            }
        )

    wms_positive_total = float(positives["_qty"].sum())
    wme_np_total = (
        float(wme_np["_qty"].sum()) if not wme_np.empty else 0.0
    )
    residual_total = float(
        sum(item["quantity"] for item in residual_wms_adjustments)
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

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
    persistent_residual_documents: list[dict[str, Any]] | None = None
    neutralized_residual_documents: list[dict[str, Any]] | None = None
    persistent_residual_total: float = 0.0
    basket_groups: list[dict[str, Any]] | None = None
    inventory_checkpoint_date: str | None = None
    safe_to_auto_explain: bool = False


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
    wms["_date"] = pd.to_datetime(
        wms.get("Data"), errors="coerce", dayfirst=True
    )

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

    wms_valid = wms[wms["_doc"].ne("")].copy()
    wms_by_doc = (
        wms_valid.groupby("_doc")["_qty"]
        .sum()
        .rename("wms_production_in")
    )
    wms_first_date_by_doc = wms_valid.groupby("_doc")["_date"].min().to_dict()
    wms_last_date_by_doc = wms_valid.groupby("_doc")["_date"].max().to_dict()
    wme_by_doc = (
        bc[bc["_doc"].ne("")]
        .groupby("_doc")["_qty"]
        .sum()
        .rename("wme_bc")
    )

    correction_by_doc: dict[str, float] = {}
    correction_rows = pd.DataFrame()
    inventory_checkpoint = None
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
        correction_rows = wms_rows[
            all_reason.eq("COR STOC")
            & all_quantity.abs().gt(tolerance)
        ].copy()
        if not correction_rows.empty:
            correction_rows["_qty"] = pd.to_numeric(
                correction_rows["Cantitate"], errors="coerce"
            ).fillna(0.0)
            correction_rows["_date"] = pd.to_datetime(
                correction_rows.get("Data"), errors="coerce", dayfirst=True
            )
            correction_rows["_details"] = (
                correction_rows["Detalii"].fillna("").astype(str)
            )
            inventory_rows = correction_rows[
                correction_rows["_details"].str.contains(
                    "INVENTAR", case=False, regex=False, na=False
                )
            ]
            if not inventory_rows.empty:
                inventory_checkpoint = inventory_rows["_date"].dropna().max()

        if correction_rows.empty:
            corrections = correction_rows.copy()
        else:
            corrections = correction_rows[
                all_operation.reindex(correction_rows.index).eq("Ajustare pozitiva")
                & correction_rows["_qty"].gt(tolerance)
            ].copy()
        if not corrections.empty:
            corrections["_qty"] = pd.to_numeric(
                corrections["Cantitate"],
                errors="coerce",
            ).fillna(0.0)
            details = corrections["Detalii"].fillna("").astype(str)
            for doc in wms_by_doc.index:
                pattern = rf"(?<!\d){re.escape(str(doc))}(?!\d)"
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
            "first_date": (
                str(wms_first_date_by_doc.get(str(doc)))
                if pd.notna(wms_first_date_by_doc.get(str(doc)))
                else None
            ),
            "last_date": (
                str(wms_last_date_by_doc.get(str(doc)))
                if pd.notna(wms_last_date_by_doc.get(str(doc)))
                else None
            ),
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

    neutralized_residual_documents: list[dict[str, Any]] = []
    persistent_residual_documents: list[dict[str, Any]] = []

    for item in residual_documents:
        item_copy = dict(item)
        doc = str(item_copy["document"])
        last_date = pd.to_datetime(
            item_copy.get("last_date"), errors="coerce"
        )
        neutralization_reason = None

        # An inventory checkpoint is not evidence that a BC mismatch was
        # corrected. Keep the document visible until an explicit reversal or
        # matching counterpart is identified. Inventory date is diagnostic only.

        if neutralization_reason is None and not correction_rows.empty:
            pattern = rf"(?<!\d){re.escape(doc)}(?!\d)"
            referenced = correction_rows[
                correction_rows["_details"].str.contains(
                    pattern,
                    case=False,
                    regex=True,
                    na=False,
                )
            ].copy()
            if pd.notna(last_date):
                referenced = referenced[
                    referenced["_date"].isna()
                    | referenced["_date"].ge(last_date)
                ]
            exact_opposite = referenced[
                (
                    referenced["_qty"]
                    + float(item_copy["difference"])
                ).abs()
                <= tolerance
            ]
            if len(exact_opposite) == 1:
                row = exact_opposite.iloc[0]
                neutralization_reason = "EXPLICIT_COR_STOC_NEUTRALIZATION"
                item_copy["neutralizing_correction"] = {
                    "date": (
                        str(row["_date"])
                        if pd.notna(row["_date"])
                        else None
                    ),
                    "quantity": float(row["_qty"]),
                    "details": str(row["_details"]),
                }

        if neutralization_reason is not None:
            item_copy["persistence_status"] = neutralization_reason
            neutralized_residual_documents.append(item_copy)
        else:
            item_copy["persistence_status"] = "PERSISTENT"
            persistent_residual_documents.append(item_copy)

    basket_groups: list[dict[str, Any]] = []
    used_in_basket: set[str] = set()
    ordered_persistent = sorted(
        persistent_residual_documents,
        key=lambda item: (
            pd.to_datetime(item.get("last_date"), errors="coerce")
            if pd.notna(pd.to_datetime(item.get("last_date"), errors="coerce"))
            else pd.Timestamp.max
        ),
    )
    for left_index, left in enumerate(ordered_persistent):
        if left["document"] in used_in_basket:
            continue
        left_date = pd.to_datetime(left.get("last_date"), errors="coerce")
        for right in ordered_persistent[left_index + 1:]:
            if right["document"] in used_in_basket:
                continue
            right_date = pd.to_datetime(right.get("last_date"), errors="coerce")
            if pd.isna(left_date) or pd.isna(right_date):
                continue
            if abs((right_date - left_date).days) > 2:
                continue
            if not (
                left.get("production_confirmed", False)
                and right.get("production_confirmed", False)
            ):
                continue

            wme_basket = (
                float(left["wme_bc"]) + float(right["wme_bc"])
            )
            left_wms = float(left["wms_effective"])
            if abs(wme_basket - left_wms) > tolerance:
                continue

            combined_difference = (
                float(left["difference"]) + float(right["difference"])
            )
            right_wms = float(right["wms_effective"])
            if abs(combined_difference - right_wms) > tolerance:
                continue

            group = {
                "documents": [
                    str(left["document"]),
                    str(right["document"]),
                ],
                "anchor_document": str(left["document"]),
                "residual_document": str(right["document"]),
                "wms_anchor": left_wms,
                "wme_basket": wme_basket,
                "persistent_effect": combined_difference,
                "status": "SPLIT_BC_BASKET_CONFIRMED",
            }
            basket_groups.append(group)
            used_in_basket.update(group["documents"])
            left["basket_group"] = group
            right["basket_group"] = group
            break

    persistent_residual_total = float(
        sum(
            float(item["difference"])
            for item in persistent_residual_documents
        )
    )
    safe_to_auto_explain = bool(
        persistent_residual_documents
        and all(
            bool(item.get("production_confirmed", False))
            for item in persistent_residual_documents
        )
    )

    return ProductionInputMatchResult(
        documents=documents,
        residual_documents=residual_documents,
        wms_total=float(comparison["wms_production_in"].sum()),
        wme_bc_total=float(comparison["wme_bc"].sum()),
        residual_total=float(comparison["difference"].sum()),
        reversed_documents=reversed_documents,
        wms_reversal_total=float(comparison["wms_reversal"].sum()),
        wms_effective_total=float(comparison["wms_effective"].sum()),
        persistent_residual_documents=persistent_residual_documents,
        neutralized_residual_documents=neutralized_residual_documents,
        persistent_residual_total=persistent_residual_total,
        basket_groups=basket_groups,
        inventory_checkpoint_date=(
            str(inventory_checkpoint)
            if inventory_checkpoint is not None
            and pd.notna(inventory_checkpoint)
            else None
        ),
        safe_to_auto_explain=safe_to_auto_explain,
    )

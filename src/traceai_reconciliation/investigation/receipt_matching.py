from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(slots=True)
class ReceiptMatchResult:
    documents: list[dict[str, Any]]
    residual_documents: list[dict[str, Any]]
    unsupported_receipts: list[dict[str, Any]]
    wms_supported_total: float
    wme_supported_total: float
    residual_total: float
    matched_wme_indexes: set[object] = field(default_factory=set)


def _document_number(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""
    match = re.search(r"(\d+)", text)
    if not match:
        return ""
    return str(int(match.group(1)))


def match_inbound_receipts(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    tolerance: float = 0.001,
) -> ReceiptMatchResult:
    """
    Match validated inbound receipt families without mixing them with returns.

    Supported mappings:
    - WMS IN... Receptie -> WME FE positive, with WME F positive as a
      document-level fallback only when FE is absent for that document;
      key = Document intrare.
    - WMS TRANSFER_CG... Receptie -> WME NT positive,
      key = Document intrare.

    RET_WME/RET_SFA and WME/WMS -1/-2 chains are handled by other matchers.
    TRANSFER_MOSE remains unsupported here until its dedicated rule is applied.
    """
    if wms_rows.empty:
        return ReceiptMatchResult([], [], [], 0.0, 0.0, 0.0)

    minimum = {"Tip operatiune", "Cantitate"}
    missing_minimum = minimum - set(wms_rows.columns)
    if missing_minimum:
        raise ValueError(
            f"WMS receipt matching: coloane de bază lipsă "
            f"{sorted(missing_minimum)}"
        )

    receipts = wms_rows[
        wms_rows["Tip operatiune"].astype(str).str.strip().eq("Receptie")
    ].copy()
    if receipts.empty:
        return ReceiptMatchResult([], [], [], 0.0, 0.0, 0.0)

    linkage_columns = {"Numar comanda", "Document intrare"}
    if not linkage_columns.issubset(receipts.columns):
        unsupported = [
            {
                "document": str(
                    row.get("Document", row.get("Numar comanda", "-"))
                ),
                "quantity": float(
                    pd.to_numeric(
                        pd.Series([row.get("Cantitate", 0.0)]),
                        errors="coerce",
                    ).fillna(0.0).iloc[0]
                ),
                "link_document": "",
                "reason": (
                    "Recepție WMS fără coloanele de legătură necesare "
                    "pentru clasificarea inbound"
                ),
                "status": "REVIEW",
            }
            for _, row in receipts.iterrows()
        ]
        return ReceiptMatchResult(
            [],
            [],
            unsupported,
            0.0,
            0.0,
            0.0,
        )

    receipts["_qty"] = pd.to_numeric(
        receipts["Cantitate"], errors="coerce"
    ).fillna(0.0)
    receipts["_raw_doc"] = (
        receipts["Numar comanda"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )
    receipts["_link_doc"] = receipts["Document intrare"].map(
        _document_number
    )

    family = pd.Series("", index=receipts.index, dtype=object)
    family.loc[receipts["_raw_doc"].str.startswith("IN")] = "SUPPLIER_IN"
    family.loc[
        receipts["_raw_doc"].str.startswith("TRANSFER_CG")
    ] = "TRANSFER_CG"
    receipts["_family"] = family

    supported = receipts[
        receipts["_family"].ne("") & receipts["_link_doc"].ne("")
    ].copy()
    unsupported = receipts[
        ~receipts.index.isin(supported.index)
    ].copy()

    op_series = wme_rows.get(
        "OperationType",
        pd.Series(index=wme_rows.index, dtype=object),
    )
    qty_series = pd.to_numeric(
        wme_rows.get(
            "SignedQuantity",
            pd.Series(index=wme_rows.index, dtype=float),
        ),
        errors="coerce",
    ).fillna(0.0)

    wme = wme_rows.copy()
    wme["_op"] = op_series.astype(str).str.strip().str.upper()
    wme["_qty"] = qty_series
    wme["_doc"] = wme.get(
        "Document",
        pd.Series(index=wme.index, dtype=object),
    ).map(_document_number)

    documents: list[dict[str, Any]] = []
    residual_documents: list[dict[str, Any]] = []

    # C-REC-003: FE has priority; F is a document-level fallback only
    # when FE is absent for the same supplier receipt document.
    family_specs = {
        "SUPPLIER_IN": ("FE", "F"),
        "TRANSFER_CG": ("NT",),
    }

    matched_wme_indexes: set[object] = set()
    wms_supported_total = 0.0
    wme_supported_total = 0.0

    for family_name, wme_types in family_specs.items():
        wms_family = supported[
            supported["_family"].eq(family_name)
        ]
        if wms_family.empty:
            continue

        wms_by_doc = (
            wms_family.groupby("_link_doc")["_qty"]
            .sum()
            .rename("wms_qty")
        )

        relevant_docs = set(wms_by_doc.index)
        wme_family = wme[
            wme["_op"].isin(wme_types)
            & wme["_qty"].gt(0)
            & wme["_doc"].isin(relevant_docs)
        ]
        wme_by_type_doc = (
            wme_family.groupby(["_op", "_doc"])["_qty"]
            .sum()
            .to_dict()
        )

        for document, wms_qty_value in wms_by_doc.sort_index().items():
            wms_qty = float(wms_qty_value)
            selected_type = wme_types[0]
            wme_qty = 0.0
            for candidate_type in wme_types:
                candidate_qty = float(
                    wme_by_type_doc.get((candidate_type, document), 0.0)
                )
                if candidate_qty > 0.0:
                    selected_type = candidate_type
                    wme_qty = candidate_qty
                    break

            difference = wms_qty - wme_qty
            wms_supported_total += wms_qty
            wme_supported_total += wme_qty

            item = {
                "family": family_name,
                "document": str(document),
                "wme_operation_type": selected_type,
                "wms_quantity": wms_qty,
                "wme_quantity": wme_qty,
                "difference": difference,
                "status": (
                    "MATCH"
                    if abs(difference) <= tolerance
                    else "QTY_DIFF"
                ),
            }
            documents.append(item)
            # Claim only uniquely identifiable WME rows used by a full match.
            # Keep quantity differences, ambiguous indexes and non-selected
            # document types visible to the residual investigator.
            if item["status"] == "MATCH" and wme.index.is_unique:
                selected_rows = wme_family[
                    wme_family["_doc"].eq(document)
                    & wme_family["_op"].eq(selected_type)
                ]
                selected_indexes = set(selected_rows.index)
                if selected_indexes and not selected_indexes.intersection(matched_wme_indexes):
                    matched_wme_indexes.update(selected_indexes)
            if abs(difference) > tolerance:
                residual_documents.append(item)

    unsupported_receipts: list[dict[str, Any]] = []
    for _, row in unsupported.iterrows():
        unsupported_receipts.append(
            {
                "document": str(row["Numar comanda"]),
                "quantity": float(row["_qty"]),
                "link_document": row["_link_doc"],
                "reason": (
                    "Familie de recepție neclasificată de matcherul "
                    "inbound RECEIPT"
                ),
                "status": "REVIEW",
            }
        )

    residual_total = float(
        sum(item["difference"] for item in residual_documents)
    )

    return ReceiptMatchResult(
        documents=documents,
        residual_documents=residual_documents,
        unsupported_receipts=unsupported_receipts,
        wms_supported_total=wms_supported_total,
        wme_supported_total=wme_supported_total,
        residual_total=residual_total,
        matched_wme_indexes=matched_wme_indexes,
    )

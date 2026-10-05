from __future__ import annotations

import re
from dataclasses import dataclass
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
    - WMS IN... Receptie -> WME FE positive, key = Document intrare.
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

    family_specs = {
        "SUPPLIER_IN": "FE",
        "TRANSFER_CG": "NT",
    }

    wms_supported_total = 0.0
    wme_supported_total = 0.0

    for family_name, wme_type in family_specs.items():
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
            wme["_op"].eq(wme_type)
            & wme["_qty"].gt(0)
            & wme["_doc"].isin(relevant_docs)
        ]
        wme_by_doc = (
            wme_family.groupby("_doc")["_qty"]
            .sum()
            .rename("wme_qty")
        )

        comparison = pd.concat(
            [wms_by_doc, wme_by_doc],
            axis=1,
        ).fillna(0.0)
        comparison["difference"] = (
            comparison["wms_qty"] - comparison["wme_qty"]
        )

        wms_supported_total += float(
            comparison["wms_qty"].sum()
        )
        wme_supported_total += float(
            comparison["wme_qty"].sum()
        )

        for document, row in comparison.sort_index().iterrows():
            difference = float(row["difference"])
            item = {
                "family": family_name,
                "document": str(document),
                "wme_operation_type": wme_type,
                "wms_quantity": float(row["wms_qty"]),
                "wme_quantity": float(row["wme_qty"]),
                "difference": difference,
                "status": (
                    "MATCH"
                    if abs(difference) <= tolerance
                    else "QTY_DIFF"
                ),
            }
            documents.append(item)
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
    )

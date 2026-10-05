from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class DeliveryMatchResult:
    documents: list[dict[str, Any]]
    residual_documents: list[dict[str, Any]]
    wme_only_documents: list[dict[str, Any]]
    wms_net_total: float
    wme_ae_total: float
    residual_total: float
    derived_receipt_documents: int = 0
    net_zero_derived_documents: int = 0


def normalize_delivery_document(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""

    text = re.sub(r"^RET_?(?:WME|SFA)", "", text)
    text = re.sub(r"^(?:AV_WMS|WME|WMS|SFA)", "", text)
    text = re.sub(r"^R(?=\d)", "", text)

    # Keep only the leading base document number. WMS cancellation chains may
    # append suffixes such as -1/-2 or _DEL_<UUID>; UUID digits must not become
    # part of the normalized document.
    match = re.match(r"^(\d+)", text)
    if match:
        return str(int(match.group(1)))

    return text


def match_deliveries_and_returns(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    tolerance: float = 0.001,
) -> DeliveryMatchResult:
    """
    Compare net WMS deliveries after WMS return/reception chains with WME AE.

    WMS Livrare rows are aggregated by normalized document. WMS Receptie rows
    whose names carry -1/-2 or RET_WME/WMS prefixes are added back to the same
    base document. This prevents a full WMS delivery+return chain from being
    reported as a false missing AE.
    """
    if wms_rows.empty:
        return DeliveryMatchResult([], [], [], 0.0, 0.0, 0.0)

    minimum = {"Tip operatiune", "Cantitate"}
    missing_minimum = minimum - set(wms_rows.columns)
    if missing_minimum:
        raise ValueError(
            f"WMS delivery matching: coloane de bază lipsă "
            f"{sorted(missing_minimum)}"
        )

    operations = wms_rows["Tip operatiune"].astype(str).str.strip()
    has_delivery_flow = operations.isin(["Livrare", "Receptie"]).any()
    if not has_delivery_flow:
        return DeliveryMatchResult([], [], [], 0.0, 0.0, 0.0)

    if "Numar comanda" not in wms_rows.columns:
        has_delivery = operations.eq("Livrare").any()
        has_return_like_receipt = False
        if "Document" in wms_rows.columns:
            doc_values = wms_rows["Document"].astype(str).str.upper()
            has_return_like_receipt = (
                operations.eq("Receptie")
                & doc_values.str.contains(r"-[12]$|RET_WME|^WMS|^WME", regex=True)
            ).any()
        if has_delivery or has_return_like_receipt:
            raise ValueError(
                "WMS delivery matching: flux de livrare/retur existent, "
                "dar coloana 'Numar comanda' lipsește."
            )
        return DeliveryMatchResult([], [], [], 0.0, 0.0, 0.0)

    work = wms_rows.copy()
    work["_op"] = work["Tip operatiune"].astype(str).str.strip()
    work["_qty"] = pd.to_numeric(work["Cantitate"], errors="coerce").fillna(0.0)
    work["_doc"] = work["Numar comanda"].map(normalize_delivery_document)

    raw_document = (
        work["Numar comanda"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )
    transfer_delivery = raw_document.str.startswith("TRANSFER_")

    delivery = work[
        work["_op"].eq("Livrare")
        & work["_doc"].ne("")
        & ~transfer_delivery
    ].copy()

    raw_document = (
        work["Numar comanda"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )
    return_like_receipt = (
        raw_document.str.startswith("RET_WME")
        | raw_document.str.startswith("RET_SFA")
        | raw_document.str.match(r"^(?:WME|WMS|AV_WMS)\d+-(?:1|2)(?:-|$)")
    )
    receipt = work[
        work["_op"].eq("Receptie")
        & work["_doc"].ne("")
        & return_like_receipt
    ].copy()

    derived_receipt_mask = (
        raw_document.str.match(
            r"^(?:WME|WMS|AV_WMS)\d+-(?:1|2)(?:-\d+)*$"
        )
    )
    derived_receipt = work[
        work["_op"].eq("Receptie")
        & work["_doc"].ne("")
        & derived_receipt_mask
    ].copy()
    derived_documents = set(derived_receipt["_doc"].tolist())

    cancellation_adjustment = pd.DataFrame(columns=work.columns)
    if "Cod-motiv" in work.columns:
        cancellation_mask = (
            work["_op"].eq("Ajustare pozitiva")
            & work["Cod-motiv"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .eq("ANULARE COMANDA")
            & work["_doc"].ne("")
        )
        cancellation_adjustment = work[cancellation_mask].copy()

    wms_delivery = delivery.groupby("_doc")["_qty"].sum()
    positive_delivery = (
        delivery.loc[delivery["_qty"].gt(0)]
        .groupby("_doc")["_qty"]
        .sum()
        .rename("positive_delivery")
    )
    negative_delivery = (
        delivery.loc[delivery["_qty"].lt(0)]
        .groupby("_doc")["_qty"]
        .sum()
        .rename("negative_delivery")
    )
    wms_returns = receipt.groupby("_doc")["_qty"].sum()
    raw_cancellations = (
        cancellation_adjustment.groupby("_doc")["_qty"].sum()
        if not cancellation_adjustment.empty
        else pd.Series(dtype=float)
    )

    cancellation_frame = pd.concat(
        [
            raw_cancellations.rename("raw_cancellation"),
            positive_delivery,
            negative_delivery,
        ],
        axis=1,
    ).fillna(0.0)

    cancellation_frame["eligible_cancellation"] = 0.0
    has_negative_delivery = cancellation_frame["negative_delivery"].lt(0)
    uncovered_cancellation = (
        cancellation_frame["raw_cancellation"]
        - cancellation_frame["positive_delivery"]
    ).clip(lower=0.0)
    remaining_negative = (
        -cancellation_frame["negative_delivery"]
        - cancellation_frame["positive_delivery"]
    ).clip(lower=0.0)
    cancellation_frame.loc[
        has_negative_delivery,
        "eligible_cancellation",
    ] = pd.concat(
        [uncovered_cancellation, remaining_negative],
        axis=1,
    ).min(axis=1)

    wms_cancellations = cancellation_frame["eligible_cancellation"]

    wms_net = pd.concat(
        [
            wms_delivery.rename("delivery"),
            wms_returns.rename("return"),
            wms_cancellations.rename("cancellation"),
        ],
        axis=1,
    ).fillna(0.0)
    wms_net["wms_net"] = (
        wms_net["delivery"]
        + wms_net["return"]
        + wms_net["cancellation"]
    )

    op_series = wme_rows.get(
        "OperationType",
        pd.Series(index=wme_rows.index, dtype=object),
    )
    ae = wme_rows[
        op_series.astype(str).str.strip().str.upper().eq("AE")
    ].copy()
    if not ae.empty:
        ae["_doc"] = ae["Document"].map(normalize_delivery_document)
        ae["_qty"] = pd.to_numeric(
            ae["SignedQuantity"], errors="coerce"
        ).fillna(0.0)
        wme_ae = ae[ae["_doc"].ne("")].groupby("_doc")["_qty"].sum()
    else:
        wme_ae = pd.Series(dtype=float)

    relevant_documents = set(wms_net.index)
    wme_relevant = wme_ae[wme_ae.index.isin(relevant_documents)]
    wme_only = wme_ae[~wme_ae.index.isin(relevant_documents)]

    comparison = pd.concat(
        [
            wms_net["wms_net"].rename("wms_net"),
            wme_relevant.rename("wme_ae"),
        ],
        axis=1,
    ).fillna(0.0)
    comparison["difference"] = comparison["wms_net"] - comparison["wme_ae"]

    documents: list[dict[str, Any]] = []
    residual_documents: list[dict[str, Any]] = []
    wme_only_documents: list[dict[str, Any]] = [
        {
            "document": str(doc),
            "wme_ae_quantity": float(quantity),
            "status": "WME_ONLY_REVIEW",
        }
        for doc, quantity in wme_only.sort_index().items()
        if abs(float(quantity)) > tolerance
    ]
    for doc, row in comparison.sort_index().iterrows():
        difference = float(row["difference"])
        item = {
            "document": str(doc),
            "wms_net_quantity": float(row["wms_net"]),
            "wme_ae_quantity": float(row["wme_ae"]),
            "difference": difference,
            "status": "MATCH" if abs(difference) <= tolerance else "QTY_DIFF",
        }
        documents.append(item)
        if abs(difference) > tolerance:
            residual_documents.append(item)

    net_zero_derived_documents = sum(
        1
        for document in derived_documents
        if document in wms_net.index
        and abs(float(wms_net.loc[document, "wms_net"])) <= tolerance
    )

    return DeliveryMatchResult(
        documents=documents,
        residual_documents=residual_documents,
        wme_only_documents=wme_only_documents,
        wms_net_total=float(comparison["wms_net"].sum()),
        wme_ae_total=float(comparison["wme_ae"].sum()),
        residual_total=float(comparison["difference"].sum()),
        derived_receipt_documents=len(derived_documents),
        net_zero_derived_documents=net_zero_derived_documents,
    )

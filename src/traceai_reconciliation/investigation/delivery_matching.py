from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class DeliveryMatchResult:
    documents: list[dict[str, Any]]
    residual_documents: list[dict[str, Any]]
    wms_net_total: float
    wme_ae_total: float
    residual_total: float


def normalize_delivery_document(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""

    text = re.sub(r"^RET_?WME", "", text)
    text = re.sub(r"^(WME|WMS)", "", text)
    text = re.sub(r"-[12]$", "", text)
    text = re.sub(r"^R(?=\d)", "", text)

    digits = re.sub(r"\D", "", text)
    if digits:
        return str(int(digits))
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
        return DeliveryMatchResult([], [], 0.0, 0.0, 0.0)

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
        return DeliveryMatchResult([], [], 0.0, 0.0, 0.0)

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
        return DeliveryMatchResult([], [], 0.0, 0.0, 0.0)

    work = wms_rows.copy()
    work["_op"] = work["Tip operatiune"].astype(str).str.strip()
    work["_qty"] = pd.to_numeric(work["Cantitate"], errors="coerce").fillna(0.0)
    work["_doc"] = work["Numar comanda"].map(normalize_delivery_document)

    delivery = work[work["_op"].eq("Livrare") & work["_doc"].ne("")].copy()
    receipt = work[work["_op"].eq("Receptie") & work["_doc"].ne("")].copy()

    wms_delivery = delivery.groupby("_doc")["_qty"].sum()
    wms_returns = receipt.groupby("_doc")["_qty"].sum()
    wms_net = pd.concat(
        [wms_delivery.rename("delivery"), wms_returns.rename("return")],
        axis=1,
    ).fillna(0.0)
    wms_net["wms_net"] = wms_net["delivery"] + wms_net["return"]

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

    comparison = pd.concat(
        [wms_net["wms_net"].rename("wms_net"), wme_ae.rename("wme_ae")],
        axis=1,
    ).fillna(0.0)
    comparison["difference"] = comparison["wms_net"] - comparison["wme_ae"]

    documents: list[dict[str, Any]] = []
    residual_documents: list[dict[str, Any]] = []
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

    return DeliveryMatchResult(
        documents=documents,
        residual_documents=residual_documents,
        wms_net_total=float(comparison["wms_net"].sum()),
        wme_ae_total=float(comparison["wme_ae"].sum()),
        residual_total=float(comparison["difference"].sum()),
    )

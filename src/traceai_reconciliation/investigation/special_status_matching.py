from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class SpecialStatusMatchResult:
    matched_groups: list[dict[str, Any]]
    residual_wms_corrections: list[dict[str, Any]]
    explained_total: float


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def match_special_status_flow(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    wms_destination: str = "INS.DET",
    wme_warehouse: str = "DETERIORATE",
    tolerance: float = 0.001,
) -> SpecialStatusMatchResult:
    """
    Candidate matcher for special-status stock flows.

    A group is accepted only when:
    - WMS has Mutare intre gestiuni into the configured special location;
    - WME has NT on the same calendar day whose counter-warehouse is the mapped
      special warehouse;
    - WMS later has COR STOC negative adjustments in the same special location;
    - transferred quantity, WME NT quantity and absolute WMS correction total
      are equal within tolerance.

    The result is evidence for a probable operational cause, not authorization
    for stock/accounting correction.
    """
    required_wms = {
        "Data",
        "Tip operatiune",
        "Cantitate",
        "Locatie sursa",
        "Locatie destinatie",
        "Cod-motiv",
        "Lot",
    }
    missing = required_wms - set(wms_rows.columns)
    if missing:
        return SpecialStatusMatchResult([], [], 0.0)

    if wme_rows.empty:
        return SpecialStatusMatchResult([], [], 0.0)

    wms = wms_rows.copy()
    wms["Data"] = pd.to_datetime(wms["Data"], errors="coerce", dayfirst=True)
    wms["_qty"] = _num(wms["Cantitate"])
    wms["_day"] = wms["Data"].dt.date
    wms["_lot"] = wms["Lot"].astype(str).str.strip()

    transfers = wms[
        wms["Tip operatiune"].astype(str).str.strip().eq("Mutare intre gestiuni")
        & wms["Locatie destinatie"].astype(str).str.strip().eq(wms_destination)
        & wms["_qty"].gt(0)
    ].copy()

    corrections = wms[
        wms["Tip operatiune"].astype(str).str.strip().eq("Ajustare negativa")
        & wms["Locatie sursa"].astype(str).str.strip().eq(wms_destination)
        & wms["Cod-motiv"].astype(str).str.strip().str.upper().eq("COR STOC")
        & wms["_qty"].lt(0)
    ].copy()

    if transfers.empty or corrections.empty:
        return SpecialStatusMatchResult([], [], 0.0)

    wme = wme_rows.copy()
    required_wme = {"Date", "OperationType", "SignedQuantity", "Warehouse"}
    if not required_wme.issubset(wme.columns):
        return SpecialStatusMatchResult([], [], 0.0)

    wme["Date"] = pd.to_datetime(wme["Date"], errors="coerce", dayfirst=True)
    wme["_day"] = wme["Date"].dt.date
    wme["_qty"] = _num(wme["SignedQuantity"])

    nt = wme[
        wme["OperationType"].astype(str).str.strip().str.upper().eq("NT")
        & wme["Warehouse"].astype(str).str.strip().str.upper().eq(
            wme_warehouse.upper()
        )
        & wme["_qty"].gt(0)
    ].copy()

    matched_groups: list[dict[str, Any]] = []
    used_correction_indices: set[int] = set()

    for transfer_day, group in transfers.groupby("_day"):
        transfer_total = float(group["_qty"].sum())
        wme_total = float(nt.loc[nt["_day"].eq(transfer_day), "_qty"].sum())

        if abs(transfer_total - wme_total) > tolerance:
            continue

        transferred_lots = set(group["_lot"].tolist())
        candidate_corrections = corrections[
            corrections["_lot"].isin(transferred_lots)
            & ~corrections.index.isin(used_correction_indices)
            & (corrections["_day"] >= transfer_day)
        ].copy()
        if candidate_corrections.empty:
            continue

        correction_total = float(candidate_corrections["_qty"].sum())
        if abs(abs(correction_total) - transfer_total) > tolerance:
            continue

        for idx in candidate_corrections.index:
            used_correction_indices.add(idx)

        matched_groups.append(
            {
                "transfer_date": str(transfer_day),
                "wms_destination": wms_destination,
                "wme_warehouse": wme_warehouse,
                "lots": sorted(transferred_lots),
                "wms_transfer_total": transfer_total,
                "wme_nt_total": wme_total,
                "wms_correction_total": correction_total,
                "status": "CANDIDATE_MATCH",
                "evidence_level": "B",
            }
        )

    residual = corrections[
        ~corrections.index.isin(used_correction_indices)
    ].copy()
    residual_wms_corrections = [
        {
            "date": row["Data"],
            "lot": row["_lot"],
            "quantity": float(row["_qty"]),
            "location": wms_destination,
            "status": "SPECIAL_STATUS_UNMATCHED",
        }
        for _, row in residual.sort_values("Data").iterrows()
    ]

    explained_total = float(
        sum(group["wms_correction_total"] for group in matched_groups)
    )

    return SpecialStatusMatchResult(
        matched_groups=matched_groups,
        residual_wms_corrections=residual_wms_corrections,
        explained_total=explained_total,
    )

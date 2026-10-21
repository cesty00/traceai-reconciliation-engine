from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .source_readers import parse_operational_dates


@dataclass(slots=True)
class InventoryAdjustmentMatchResult:
    matches: list[dict[str, Any]]
    residual_wms_adjustments: list[dict[str, Any]]
    residual_wme_pv: list[dict[str, Any]]
    residual_wms_total: float
    residual_wme_total: float
    system_difference_effect: float
    matched_wme_indexes: tuple[object, ...]


def _audit_value(row: pd.Series, names: tuple[str, ...]) -> str | None:
    """Read optional business identifiers without inventing raw source pointers."""
    for name in names:
        if name in row.index and pd.notna(row[name]):
            value = str(row[name]).strip()
            if value and value.lower() not in {"nan", "none"}:
                return value
    return None


def _contributing_event_refs(group: pd.DataFrame) -> list[dict[str, Any]]:
    """Additive read-only lineage hints; never evidence of verified source rows."""
    refs = []
    for _, row in group.iterrows():
        refs.append({
            "document": _audit_value(row, ("Document intrare", "Document comanda", "Numar comanda", "Document", "Nr document", "Numar document", "Nr. document")),
            "lot": _audit_value(row, ("Lot", "Lot productie", "Lot produs")),
            "date": row["_date"].date().isoformat(),
            "reason": str(row["_reason"]),
            "quantity": float(row["_qty"]),
            "source_pointer_status": "UNVERIFIED",
            "document_format_status": (
                "LOSSY_NUMERIC_IMPORT"
                if any(name in row.index and isinstance(row[name], float) and pd.notna(row[name])
                       for name in ("Document intrare", "Document comanda", "Numar comanda"))
                else "UNVERIFIED"
            ),
        })
    return refs


def match_inventory_adjustments(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    *,
    tolerance: float = 0.001,
    max_day_gap: int = 1,
) -> InventoryAdjustmentMatchResult:
    """Match explicit WMS INV-PLS/INV-MIN inventory events to WME PV."""
    wms = wms_rows.copy()
    if not wms.empty and {"Data", "Tip operatiune", "Cantitate", "Cod-motiv"}.issubset(wms):
        wms["_date"] = parse_operational_dates(wms["Data"])
        wms["_reason"] = wms["Cod-motiv"].astype(str).str.strip().str.upper()
        wms["_qty"] = pd.to_numeric(wms["Cantitate"], errors="coerce").fillna(0.0)
        wms = wms[
            wms["Tip operatiune"].astype(str).str.strip().isin(
                {"Ajustare pozitiva", "Ajustare negativa"}
            )
            & wms["_reason"].isin({"INV-PLS", "INV-MIN"})
            & wms["_qty"].ne(0.0)
            & wms["_date"].notna()
        ].copy()
    else:
        wms = pd.DataFrame()

    wme = wme_rows.copy()
    if not wme.empty and {"Date", "OperationType", "SignedQuantity"}.issubset(wme):
        wme["_date"] = parse_operational_dates(wme["Date"])
        wme["_qty"] = pd.to_numeric(wme["SignedQuantity"], errors="coerce").fillna(0.0)
        wme = wme[
            wme["OperationType"].astype(str).str.strip().str.upper().eq("PV")
            & wme["_qty"].ne(0.0)
            & wme["_date"].notna()
        ].copy()
    else:
        wme = pd.DataFrame()

    wgroups = []
    if not wms.empty:
        wms["_day"] = wms["_date"].dt.normalize()
        for (day, reason), group in wms.groupby(["_day", "_reason"]):
            wgroups.append({
                "day": day, "reason": reason,
                "qty": round(float(group["_qty"].sum()), 6),
                "rows": len(group),
                "contributing_event_refs": _contributing_event_refs(group),
            })

    pgroups = []
    if not wme.empty:
        wme["_day"] = wme["_date"].dt.normalize()
        doc = "Document" if "Document" in wme.columns else None
        wh = "Warehouse" if "Warehouse" in wme.columns else None
        keys = ["_day"] + ([doc] if doc else []) + ([wh] if wh else [])
        for key, group in wme.groupby(keys, dropna=False):
            if not isinstance(key, tuple):
                key = (key,)
            pgroups.append({
                "day": key[0],
                "document": str(key[1]) if doc else "",
                "warehouse": str(key[2 if doc else 1]) if wh else "",
                "qty": round(float(group["_qty"].sum()), 6),
                "rows": len(group),
                "indexes": tuple(group.index.tolist()),
            })

    candidates = []
    for wi, w in enumerate(wgroups):
        for pi, p in enumerate(pgroups):
            if abs(w["qty"] - p["qty"]) > tolerance:
                continue
            if abs((w["day"] - p["day"]).days) <= max_day_gap:
                candidates.append((wi, pi))

    wc = {i: sum(1 for wi, _ in candidates if wi == i) for i in range(len(wgroups))}
    pc = {i: sum(1 for _, pi in candidates if pi == i) for i in range(len(pgroups))}
    accepted = [(wi, pi) for wi, pi in candidates if wc[wi] == 1 and pc[pi] == 1]
    mw = {wi for wi, _ in accepted}
    mp = {pi for _, pi in accepted}

    matches = []
    matched_indexes = []
    for wi, pi in accepted:
        w, p = wgroups[wi], pgroups[pi]
        matched_indexes.extend(p["indexes"])
        matches.append({
            "wms_date": w["day"].isoformat(),
            "wme_date": p["day"].isoformat(),
            "wms_reason": w["reason"],
            "wme_operation_type": "PV",
            "wme_document": p["document"],
            "wme_warehouse": p["warehouse"],
            "quantity": w["qty"],
            "day_gap": abs((w["day"] - p["day"]).days),
            "status": "MATCH",
        })

    residual_wms = [
        {"date": w["day"].isoformat(), "reason": w["reason"], "quantity": w["qty"],
         "status": "WMS_ONLY_INVENTORY_REVIEW",
         "contributing_event_refs": w["contributing_event_refs"]}
        for i, w in enumerate(wgroups) if i not in mw
    ]
    residual_wme = [
        {"date": p["day"].isoformat(), "document": p["document"],
         "warehouse": p["warehouse"], "quantity": p["qty"],
         "status": "WME_ONLY_PV_REVIEW"}
        for i, p in enumerate(pgroups) if i not in mp
    ]

    rw = round(float(sum(x["quantity"] for x in residual_wms)), 6)
    rp = round(float(sum(x["quantity"] for x in residual_wme)), 6)
    return InventoryAdjustmentMatchResult(
        matches=matches,
        residual_wms_adjustments=residual_wms,
        residual_wme_pv=residual_wme,
        residual_wms_total=rw,
        residual_wme_total=rp,
        system_difference_effect=round(rw - rp, 6),
        matched_wme_indexes=tuple(matched_indexes),
    )

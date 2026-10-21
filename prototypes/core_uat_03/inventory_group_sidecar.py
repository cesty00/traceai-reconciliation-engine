"""CORE-UAT-04F isolated grouping-sidecar experiment; never changes CORE matcher.

Preserves source records for audit while independently comparing matcher outputs.
This is NOT validated physical source provenance.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any
import pandas as pd

from traceai_reconciliation.investigation.source_readers import parse_operational_dates


def inventory_group_sidecar(wms_rows: pd.DataFrame) -> list[dict[str, Any]]:
    required = {"Data", "Tip operatiune", "Cantitate", "Cod-motiv", "Document", "Lot"}
    if not required.issubset(wms_rows.columns):
        raise ValueError("missing required columns: " + str(sorted(required - set(wms_rows.columns))))
    rows = wms_rows.copy()
    rows["_day"] = parse_operational_dates(rows["Data"]).dt.normalize()
    rows["_reason"] = rows["Cod-motiv"].astype(str).str.strip().str.upper()
    rows["_qty"] = pd.to_numeric(rows["Cantitate"], errors="coerce")
    rows = rows[
        rows["Tip operatiune"].astype(str).str.strip().isin(
            {"Ajustare pozitiva", "Ajustare negativa"}
        ) & rows["_reason"].isin({"INV-PLS", "INV-MIN"})
        & rows["_day"].notna() & rows["_qty"].notna() & rows["_qty"].ne(0.0)
    ]
    result = []
    for (day, reason), group in rows.groupby(["_day", "_reason"]):
        events = [{"document": str(r["Document"]), "lot": str(r["Lot"]),
                   "quantity": float(r["_qty"]), "source_pointer_status": "UNVERIFIED"}
                  for _, r in group.iterrows()]
        result.append({"date": day.isoformat(), "reason": reason,
                       "quantity": round(sum(e["quantity"] for e in events), 6),
                       "contributing_events": events})
    return result

from __future__ import annotations

from typing import Any

import pandas as pd

from .source_readers import resolve_column


def _row_value(
    row: pd.Series,
    columns: pd.Index,
    semantic: str,
    default: Any = "-",
) -> Any:
    column = resolve_column(columns, semantic, required=False)
    if column is None:
        return default
    value = row.get(column, default)
    if pd.isna(value):
        return default
    return value


def timeline_from_wms(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    entries: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        entries.append(
            {
                "date": _row_value(row, df.columns, "date"),
                "system": "WMS",
                "document": _row_value(row, df.columns, "document"),
                "operation_type": _row_value(row, df.columns, "operation_type"),
                "quantity": _row_value(row, df.columns, "quantity"),
                "warehouse": _row_value(row, df.columns, "warehouse"),
                "counterpart": "-",
                "verdict": "REVIEW",
                "note": "Operațiune WMS extrasă automat pentru produs.",
            }
        )
    return entries


def timeline_from_wme(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    entries: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        entries.append(
            {
                "date": row.get("Date", "-"),
                "system": "WME",
                "document": row.get("Document", "-"),
                "operation_type": row.get("OperationType", "-"),
                "quantity": row.get("SignedQuantity", "-"),
                "warehouse": row.get("Warehouse", "-"),
                "counterpart": row.get("Partner", "-"),
                "verdict": "REVIEW",
                "note": f"Sold după operațiune: {row.get('Balance', '-')}",
            }
        )
    return entries


def timeline_from_production(
    df: pd.DataFrame,
    product_code: str,
) -> list[dict[str, Any]]:
    if df.empty:
        return []

    entries: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        kind = str(row.get("TipLinie", "")).strip().upper()
        if kind == "PREDARE":
            code = str(row.get("PRE_Cod Articol", "")).strip()
            if code != str(product_code).strip():
                continue
            qty = row.get("PRE_Cantitate Predare", "-")
            unit = row.get("PRE_U.M.", "-")
        elif kind == "CONSUM":
            code = str(row.get("CON_Cod Articol", "")).strip()
            if code != str(product_code).strip():
                continue
            qty = row.get("CON_Cantitate Consumata", "-")
            unit = row.get("CON_U.M.", "-")
        else:
            continue

        entries.append(
            {
                "date": row.get("Data Start", "-"),
                "system": "PRODUCTIE",
                "document": row.get("Numar Comanda", "-"),
                "operation_type": kind,
                "quantity": qty,
                "warehouse": row.get("Utilaj Productie", "-"),
                "counterpart": "-",
                "verdict": "REVIEW",
                "note": f"UM producție: {unit}",
            }
        )
    return entries

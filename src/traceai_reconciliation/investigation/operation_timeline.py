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




def _identifier_text(value: Any, field: str) -> str:
    """Don't show spreadsheet float suffixes for integral pallet identifiers."""
    from numbers import Integral, Real
    if field == "pallet" and isinstance(value, Real) and not isinstance(value, bool):
        if float(value).is_integer():
            return str(int(value))
    if field == "pallet" and isinstance(value, str):
        import re
        if re.fullmatch(r"[0-9]+\.0+", value.strip()):
            return value.strip().split(".")[0]
    return str(value).strip()


def _explicit_wms_metadata(row: pd.Series) -> dict[str, Any]:
    """Copy only explicitly named source fields; never derive logistics IDs."""
    from .source_readers import normalize_header

    accepted = {
        "nir": ("NIR", "Nr NIR", "Numar NIR", "NIR Number"),
        "pallet": ("Palet", "Cod palet", "ID palet", "Pallet", "Pallet ID"),
        "lot": ("Lot", "Lot produs", "LotArticol"),
        "location": ("Locatie", "Locatie WMS", "Cod locatie", "Location"),
    }
    available = {normalize_header(column): column for column in row.index}
    metadata = {}
    for name, aliases in accepted.items():
        keys = [available[normalize_header(a)] for a in aliases
                if normalize_header(a) in available]
        keys = list(dict.fromkeys(keys))
        if len(keys) != 1:
            continue
        value = row.get(keys[0])
        if value is not None and not pd.isna(value) and str(value).strip() not in ("", "-"):
            metadata[name] = _identifier_text(value, name)
    # The physical WMS trace export uses separate source/destination fields.
    # Only on actual receipts is the destination pallet/location the received stock.
    operation = str(_row_value(row, row.index, "operation_type", "")).strip().casefold()
    if operation in ("receptie", "recepție"):
        for field, source_column in (
            ("nir", "Document comanda"),
            ("pallet", "Palet destinatie"),
            ("location", "Locatie destinatie"),
        ):
            matching = [c for c in row.index
                        if normalize_header(c) == normalize_header(source_column)]
            if len(matching) == 1:
                value = row.get(matching[0])
                if value is not None and not pd.isna(value) and str(value).strip() not in ("", "-"):
                    if field not in metadata:
                        metadata[field] = _identifier_text(value, field)
                    elif metadata[field] != _identifier_text(value, field):
                        metadata.pop(field, None)
    return metadata



def _source_actor(row: pd.Series) -> dict[str, str]:
    """Read explicit user/person columns only; never infer an actor from a partner."""
    from .source_readers import normalize_header
    accepted = {
        "user": ("Utilizator", "User", "Username", "User Name", "User operare",
                 "Utilizator operare", "Operat de", "Creat de"),
        "person": ("Operator", "Nume operator", "Nume persoana", "Persoana",
                   "Responsabil operatiune", "Participant"),
    }
    normalized = {normalize_header(col): col for col in row.index}
    out = {}
    for field, aliases in accepted.items():
        columns = list(dict.fromkeys(
            normalized[normalize_header(alias)]
            for alias in aliases if normalize_header(alias) in normalized
        ))
        if len(columns) != 1:
            continue
        value = row.get(columns[0])
        if value is not None and not pd.isna(value):
            clean = str(value).strip()
            if clean and clean.casefold() not in ("-", "nan", "none"):
                out[field] = clean
    return out


def timeline_from_wms(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    entries: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        entries.append(
            {
                "date": _row_value(row, df.columns, "date"),
                "system": "WMS",
                **({"wms_details": str(row[detail_col])} if (detail_col := next((c for c in row.index if str(c).strip().casefold() == "detalii"), None)) is not None and pd.notna(row[detail_col]) and str(row[detail_col]).strip() else {}),
                **({"actor": _source_actor(row)} if _source_actor(row) else {}),
                **({"source_metadata": _explicit_wms_metadata(row)} if _explicit_wms_metadata(row) else {}),
                "source_row": row.get("SourceRowNumber") if pd.notna(row.get("SourceRowNumber")) else None,
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
                **({"actor": {"user": str(row.get("Note")).strip()}} if pd.notna(row.get("Note")) and str(row.get("Note")).strip() not in ("", "-", "nan", "None") else {}),
                "source_row": row.get("SourceRowNumber") if pd.notna(row.get("SourceRowNumber")) else None,
                "source_line_no": row.get("LineNo") if pd.notna(row.get("LineNo")) else None,
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
                **({"actor": _source_actor(row)} if _source_actor(row) else {}),
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

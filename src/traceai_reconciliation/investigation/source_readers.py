from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
from openpyxl import load_workbook


ALIASES: dict[str, tuple[str, ...]] = {
    "product_code": (
        "CodArticol", "Cod articol", "Cod produs", "Cod DS", "Cod WMS",
        "Cod produs WMS/DS", "DS", "ProductCode",
    ),
    "product_name": (
        "DenumireArticol", "Denumire articol", "Denumire produs", "Produs", "ProductName",
    ),
    "quantity": (
        "Cantitate", "Quantity", "Qty", "Cant", "Cantitate operata",
    ),
    "unit": ("UM", "U.M.", "Unitate masura", "Unit"),
    "date": (
        "Data", "Data operatie", "Data operatiune", "Data document", "Date", "DataDoc",
    ),
    "document": (
        "Document", "NrDocument", "Nr document", "Numar document", "Numar", "NrDoc",
        "Comanda", "Numar Comanda", "Order",
    ),
    "operation_type": (
        "Tip operatiune", "Tip operatie", "Operatiune", "Tip document", "TipDoc",
        "Tip", "OperationType",
    ),
    "warehouse": (
        "Gestiune", "Depozit", "Locatie", "Warehouse", "Gestiune sursa",
    ),
    "running_balance": (
        "Stoc", "Sold", "Stoc la data", "Sold final", "Balance",
    ),
    "wme_item_id": (
        "ID articol WME", "Id articol WME", "ID articol", "IdArticol", "idArticol",
        "Cod articol WME", "CodArticolWME", "ArticolID",
    ),
    "wms_product_code": (
        "Cod produs WMS/DS", "Cod WMS/DS", "Cod DS", "Cod WMS", "CodArticolWMS",
        "CodArticol", "Cod produs",
    ),
    "stock_wme": ("QuantityERP", "Stoc ERP", "Stoc WME", "QuantityWME"),
    "stock_wms": ("QuantityWMS", "Stoc WMS"),
    "stock_difference": ("QuantityDifference", "Diferenta", "Diferență"),
    "initial_stock": ("StocInitial", "Stoc initial", "Stoc inițial", "Quantity", "Cantitate", "Stoc"),
    "production_kind": ("Tip", "Tip operatie", "Tip operatiune", "CONSUM/PREDARE", "Miscare"),
    "lot": ("Lot", "Lot produs", "LotArticol"),
}


def normalize_header(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    return re.sub(r"[^a-z0-9]+", "", text)


def resolve_column(columns: Sequence[object], semantic_name: str, required: bool = True) -> str | None:
    candidates = ALIASES.get(semantic_name, ())
    normalized = {normalize_header(col): str(col) for col in columns}
    for alias in candidates:
        key = normalize_header(alias)
        if key in normalized:
            return normalized[key]
    if required:
        raise ValueError(
            f"Nu pot rezolva coloana '{semantic_name}'. Coloane disponibile: {list(map(str, columns))}"
        )
    return None


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def detect_csv_delimiter(path: str | Path) -> str:
    path = Path(path)
    sample = path.read_bytes()[:65536]
    for encoding in ("utf-8-sig", "utf-8", "cp1250", "latin1"):
        try:
            text = sample.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        return ","
    try:
        dialect = csv.Sniffer().sniff(text, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ";" if text.count(";") > text.count(",") else ","


def _string_mask(series: pd.Series, accepted_values: set[str]) -> pd.Series:
    normalized = series.astype(str).str.strip()
    return normalized.isin(accepted_values)


def filter_csv_by_values(
    path: str | Path,
    semantic_column: str,
    accepted_values: Iterable[str],
    chunksize: int = 50000,
) -> pd.DataFrame:
    path = Path(path)
    accepted = {str(value).strip() for value in accepted_values}
    delimiter = detect_csv_delimiter(path)
    chunks: list[pd.DataFrame] = []
    resolved_column: str | None = None

    read_kwargs = {
        "sep": delimiter,
        "chunksize": chunksize,
        "low_memory": False,
        "encoding": "utf-8-sig",
    }
    try:
        iterator = pd.read_csv(path, **read_kwargs)
        for chunk in iterator:
            if resolved_column is None:
                resolved_column = resolve_column(chunk.columns, semantic_column)
            mask = _string_mask(chunk[resolved_column], accepted)
            if mask.any():
                chunks.append(chunk.loc[mask].copy())
    except UnicodeDecodeError:
        read_kwargs["encoding"] = "cp1250"
        iterator = pd.read_csv(path, **read_kwargs)
        for chunk in iterator:
            if resolved_column is None:
                resolved_column = resolve_column(chunk.columns, semantic_column)
            mask = _string_mask(chunk[resolved_column], accepted)
            if mask.any():
                chunks.append(chunk.loc[mask].copy())

    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


def read_excel_table(path: str | Path) -> pd.DataFrame:
    return pd.read_excel(Path(path))


def filter_xlsx_by_values(
    path: str | Path,
    semantic_column: str,
    accepted_values: Iterable[str],
) -> pd.DataFrame:
    path = Path(path)
    accepted = {str(value).strip() for value in accepted_values}
    workbook = load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]
    rows = worksheet.iter_rows(values_only=True)

    try:
        headers = list(next(rows))
    except StopIteration:
        workbook.close()
        return pd.DataFrame()

    column = resolve_column(headers, semantic_column)
    index = headers.index(column)
    matches: list[tuple[object, ...]] = []

    for row in rows:
        value = row[index] if index < len(row) else None
        if str(value).strip() in accepted:
            matches.append(tuple(row))

    workbook.close()
    if not matches:
        return pd.DataFrame(columns=headers)
    return pd.DataFrame(matches, columns=headers)


def read_filtered(
    path: str | Path,
    semantic_column: str,
    accepted_values: Iterable[str],
) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return filter_csv_by_values(path, semantic_column, accepted_values)
    if suffix == ".xlsx":
        return filter_xlsx_by_values(path, semantic_column, accepted_values)
    if suffix == ".xls":
        raise ValueError(
            f"{path.name}: format .xls neacceptat în citirea filtrată. Convertește sursa la .xlsx fără a modifica datele."
        )
    raise ValueError(f"Format sursă neacceptat: {path.suffix}")


def numeric_sum(df: pd.DataFrame, semantic_column: str) -> float:
    if df.empty:
        return 0.0
    column = resolve_column(df.columns, semantic_column)
    values = pd.to_numeric(df[column], errors="coerce").fillna(0)
    return float(values.sum())


def first_non_empty(df: pd.DataFrame, semantic_column: str) -> str | None:
    if df.empty:
        return None
    column = resolve_column(df.columns, semantic_column, required=False)
    if column is None:
        return None
    values = df[column].dropna().astype(str).str.strip()
    values = values[values != ""]
    return values.iloc[0] if not values.empty else None

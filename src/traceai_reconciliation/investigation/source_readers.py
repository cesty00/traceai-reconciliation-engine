from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from datetime import datetime
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
        "DenumireArticol", "Denumire articol", "Denumire produs", "Produs",
        "ProductName", "productname", "Denumire",
    ),
    "quantity": (
        "Cantitate", "cantitate", "Quantity", "Qty", "Cant", "Cantitate operata",
        "SignedQuantity",
    ),
    "unit": ("UM", "U.M.", "Unitate masura", "Unit", "U.M."),
    "date": (
        "Data", "Data operatie", "Data operatiune", "Data document", "Date",
        "DataDoc", "Data Start",
    ),
    "document": (
        "Document", "NrDocument", "Nr document", "Numar document", "Numar",
        "NrDoc", "Comanda", "Numar Comanda", "Numar comanda", "Order",
    ),
    "operation_type": (
        "Tip operatiune", "Tip operatie", "Operatiune", "Tip document",
        "TipDoc", "Tip", "OperationType", "TipLinie",
    ),
    "warehouse": (
        "Gestiune", "Depozit", "Locatie", "Warehouse", "Gestiune sursa",
    ),
    "running_balance": (
        "Stoc", "Sold", "Stoc la data", "Sold final", "Balance",
    ),
    "wme_item_id": (
        "ID articol WME", "Id articol WME", "ID articol", "IdArticol",
        "idArticol", "Cod articol WME", "CodArticolWME", "ArticolID",
        "WMEItemId",
    ),
    "wms_product_code": (
        "Cod produs WMS/DS", "Cod WMS/DS", "Cod DS", "Cod WMS",
        "CodArticolWMS", "CodArticol", "Cod produs", "Cod articol",
    ),
    "stock_wme": ("QuantityERP", "Stoc ERP", "Stoc WME", "QuantityWME"),
    "stock_wms": ("QuantityWMS", "Stoc WMS"),
    "stock_difference": ("QuantityDifference", "Diferenta", "Diferență"),
    "initial_stock": (
        "StocInitial", "Stoc initial", "Stoc inițial", "Quantity",
        "Cantitate", "cantitate", "Stoc",
    ),
    "lot": ("Lot", "Lot produs", "LotArticol"),
}


def normalize_header(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    return re.sub(r"[^a-z0-9]+", "", text)


def resolve_column(
    columns: Sequence[object], semantic_name: str, required: bool = True
) -> str | None:
    candidates = ALIASES.get(semantic_name, ())
    normalized = {normalize_header(col): str(col) for col in columns}
    for alias in candidates:
        key = normalize_header(alias)
        if key in normalized:
            return normalized[key]
    if required:
        raise ValueError(
            f"Nu pot rezolva coloana '{semantic_name}'. "
            f"Coloane disponibile: {list(map(str, columns))}"
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
        return ";"

    first_line = text.splitlines()[0] if text.splitlines() else text
    counts = {delimiter: first_line.count(delimiter) for delimiter in (";", ",", "\t", "|")}
    best = max(counts, key=counts.get)
    if counts[best] > 0:
        return best

    try:
        return csv.Sniffer().sniff(text, delimiters=",;\t|").delimiter
    except csv.Error:
        return ";"


def parse_period(period: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    tokens = re.findall(r"\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}", str(period))
    if len(tokens) != 2:
        raise ValueError(
            "Perioada trebuie să conțină exact două date, de exemplu "
            "'01.01.2026-04.10.2026'."
        )

    def parse_one(value: str) -> pd.Timestamp:
        if "." in value:
            return pd.Timestamp(datetime.strptime(value, "%d.%m.%Y"))
        return pd.Timestamp(datetime.strptime(value, "%Y-%m-%d"))

    start, end = map(parse_one, tokens)
    if start > end:
        raise ValueError("Data de început este după data de sfârșit.")
    return start, end


def filter_by_period(
    df: pd.DataFrame,
    period: str,
    semantic_date_column: str = "date",
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    date_col = resolve_column(df.columns, semantic_date_column, required=False)
    if date_col is None:
        return df.copy()

    start, end = parse_period(period)
    parsed = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    mask = parsed.between(start, end + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1))
    result = df.loc[mask].copy()
    result[date_col] = parsed.loc[mask]
    return result


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

    for encoding in ("utf-8-sig", "cp1250", "latin1"):
        try:
            iterator = pd.read_csv(
                path,
                sep=delimiter,
                chunksize=chunksize,
                low_memory=False,
                encoding=encoding,
            )
            for chunk in iterator:
                if resolved_column is None:
                    resolved_column = resolve_column(chunk.columns, semantic_column)
                mask = _string_mask(chunk[resolved_column], accepted)
                if mask.any():
                    chunks.append(chunk.loc[mask].copy())
            break
        except UnicodeDecodeError:
            chunks = []
            resolved_column = None
            continue

    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


def read_excel_table(path: str | Path, sheet_name: str | int = 0) -> pd.DataFrame:
    return pd.read_excel(Path(path), sheet_name=sheet_name)


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
            f"{path.name}: format .xls neacceptat în citirea filtrată. "
            "Convertește sursa la .xlsx fără a modifica datele."
        )
    raise ValueError(f"Format sursă neacceptat: {path.suffix}")


def read_production_product(
    path: str | Path,
    product_code: str,
    period: str | None = None,
    chunksize: int = 50000,
) -> pd.DataFrame:
    path = Path(path)
    delimiter = detect_csv_delimiter(path)
    matches: list[pd.DataFrame] = []

    iterator = pd.read_csv(
        path,
        sep=delimiter,
        chunksize=chunksize,
        low_memory=False,
        encoding="utf-8-sig",
    )
    for chunk in iterator:
        direct = resolve_column(chunk.columns, "product_code", required=False)
        if direct is not None:
            mask = chunk[direct].astype(str).str.strip().eq(str(product_code).strip())
        else:
            pre = next(
                (c for c in chunk.columns if normalize_header(c) == normalize_header("PRE_Cod Articol")),
                None,
            )
            con = next(
                (c for c in chunk.columns if normalize_header(c) == normalize_header("CON_Cod Articol")),
                None,
            )
            if pre is None and con is None:
                raise ValueError(
                    f"{path.name}: nu găsesc PRE_Cod Articol / CON_Cod Articol."
                )
            mask = pd.Series(False, index=chunk.index)
            if pre is not None:
                mask |= chunk[pre].astype(str).str.strip().eq(str(product_code).strip())
            if con is not None:
                mask |= chunk[con].astype(str).str.strip().eq(str(product_code).strip())

        if mask.any():
            matches.append(chunk.loc[mask].copy())

    result = pd.concat(matches, ignore_index=True) if matches else pd.DataFrame()
    return filter_by_period(result, period) if period and not result.empty else result


WME_STANDARD_COLUMNS = [
    "LineNo",
    "OperationType",
    "Document",
    "Date",
    "Incoming",
    "Outgoing",
    "Balance",
    "Price",
    "Account",
    "Partner",
    "ProductName",
    "CounterWarehouse",
    "WMEItemId",
    "Warehouse",
    "Unit",
    "Note",
    "InternalRef",
    "SignedQuantity",
]


def read_wme_product(
    path: str | Path,
    product_name: str,
    period: str | None = None,
) -> tuple[pd.DataFrame, set[str]]:
    path = Path(path)
    workbook = load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]

    rows: list[dict[str, object]] = []
    ids: set[str] = set()

    for row in worksheet.iter_rows(values_only=True):
        if len(row) < 15:
            continue
        current_name = str(row[10] or "").strip()
        if current_name != str(product_name).strip():
            continue

        item_id = str(row[12] or "").strip()
        if item_id:
            ids.add(item_id)

        incoming = pd.to_numeric(pd.Series([row[4]]), errors="coerce").iloc[0]
        outgoing = pd.to_numeric(pd.Series([row[5]]), errors="coerce").iloc[0]
        incoming = 0.0 if pd.isna(incoming) else float(incoming)
        outgoing = 0.0 if pd.isna(outgoing) else float(outgoing)

        rows.append(
            {
                "LineNo": row[0],
                "OperationType": row[1],
                "Document": row[2],
                "Date": row[3],
                "Incoming": incoming,
                "Outgoing": outgoing,
                "Balance": row[6],
                "Price": row[7],
                "Account": row[8],
                "Partner": row[9],
                "ProductName": current_name,
                "CounterWarehouse": row[11],
                "WMEItemId": item_id,
                "Warehouse": row[13],
                "Unit": row[14],
                "Note": row[15] if len(row) > 15 else None,
                "InternalRef": row[16] if len(row) > 16 else None,
                "SignedQuantity": incoming - outgoing,
            }
        )

    workbook.close()
    result = pd.DataFrame(rows, columns=WME_STANDARD_COLUMNS)
    if period and not result.empty:
        result = filter_by_period(result, period)
    return result, ids


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

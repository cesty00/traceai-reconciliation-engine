from __future__ import annotations

import pandas as pd

from .models import ProductAudit


def round_qty(value: float, decimals: int = 3) -> float:
    return round(float(value), decimals)


def filter_product(
    df: pd.DataFrame,
    product_code: str,
    code_column: str,
) -> pd.DataFrame:
    """Return only rows belonging to one product code."""
    mask = df[code_column].astype(str).str.strip() == str(product_code).strip()
    return df.loc[mask].copy()


def summarize_stock_report(
    report_df: pd.DataFrame,
    product_code: str,
    code_column: str = "CodArticol",
    name_column: str = "DenumireArticol",
    erp_column: str = "QuantityERP",
    wms_column: str = "QuantityWMS",
    diff_column: str = "QuantityDifference",
    decimals: int = 3,
) -> ProductAudit:
    rows = filter_product(report_df, product_code, code_column)
    if rows.empty:
        raise KeyError(f"Product not found in stock report: {product_code}")

    product_name = str(rows[name_column].dropna().iloc[0]) if rows[name_column].notna().any() else None
    erp = round_qty(rows[erp_column].fillna(0).sum(), decimals)
    wms = round_qty(rows[wms_column].fillna(0).sum(), decimals)
    diff = round_qty(rows[diff_column].fillna(0).sum(), decimals)

    return ProductAudit(
        product_code=str(product_code),
        product_name=product_name,
        reported_stock_wme=erp,
        reported_stock_wms=wms,
        difference_reported=diff,
        details={"stock_report_rows": len(rows)},
    )

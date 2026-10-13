from __future__ import annotations

import pandas as pd

from .source_readers import resolve_column


def validate_nomenclature(
    nomenclature: pd.DataFrame,
    product_code: str,
    product_name: str,
) -> tuple[str, str]:
    """Validate product-code/name consistency without inferring missing mappings."""
    if nomenclature.empty:
        return "ABSENT", "D"

    code_col = resolve_column(
        nomenclature.columns,
        "wms_product_code",
        required=False,
    )
    name_col = resolve_column(
        nomenclature.columns,
        "product_name",
        required=False,
    )
    if code_col is None:
        return "ABSENT", "D"

    rows = nomenclature[
        nomenclature[code_col].astype(str).str.strip()
        == str(product_code).strip()
    ].copy()
    if rows.empty:
        return "COD_LIPSA", "C"

    if name_col is None:
        return "COD_CONFIRMAT", "B"

    names = {
        str(value).strip()
        for value in rows[name_col].dropna().tolist()
        if str(value).strip()
    }
    if product_name in names and len(names) == 1:
        return "COD_SI_DENUMIRE_CONFIRMATE", "A"
    if product_name in names:
        return "COD_CONFIRMAT_DENUMIRE_AMBIGUA", "B"
    return "COD_CONFIRMAT_DENUMIRE_DIFERITA", "C"

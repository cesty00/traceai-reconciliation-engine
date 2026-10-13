from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .source_readers import first_non_empty


@dataclass(frozen=True, slots=True)
class ProductIdentityResolution:
    unit: str
    warnings: tuple[str, ...]


def resolve_product_identity(
    *,
    current_unit: str,
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    wme_ids: set[str],
    product_code: str,
    product_name: str,
    nomenclature_status: str,
) -> ProductIdentityResolution:
    """Resolve display unit and identity warnings without changing mappings."""
    unit = current_unit
    if not wms_rows.empty:
        wms_unit = first_non_empty(wms_rows, "unit")
        if wms_unit:
            unit = wms_unit

    if unit == "UM" and not wme_rows.empty:
        wme_units = [
            str(value).strip()
            for value in wme_rows["Unit"].dropna().tolist()
            if str(value).strip()
        ]
        if wme_units:
            unit = wme_units[0]

    warnings: list[str] = []
    if not wme_ids:
        warnings.append(
            f"Denumirea exactă '{product_name}' nu a fost găsită în fișa WME."
        )
    elif len(wme_ids) > 1:
        warnings.append(
            f"Denumirea exactă '{product_name}' este asociată cu mai multe ID-uri WME: "
            f"{sorted(wme_ids)}."
        )
    elif nomenclature_status == "COD_LIPSA":
        warnings.append(
            f"Codul {product_code} lipsește din nomenclatorul încărcat. "
            f"Extragerea WME folosește denumirea exactă din raportul de stoc, "
            f"care conduce univoc la ID WME {next(iter(wme_ids))}. "
            "Maparea rămâne de validat înainte să devină regulă generală."
        )

    return ProductIdentityResolution(
        unit=unit,
        warnings=tuple(warnings),
    )

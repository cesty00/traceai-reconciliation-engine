from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import InvestigationSources
from .source_readers import numeric_sum, read_filtered


@dataclass(frozen=True, slots=True)
class OpeningStockResolution:
    value: float | None
    warning: str | None
    details: dict[str, Any]


def resolve_opening_stock_wms(
    sources: InvestigationSources,
    *,
    product_code: str,
    decimals: int,
) -> OpeningStockResolution:
    """Resolve opening WMS stock under the explicit absence policy."""
    opening_rows = read_filtered(
        sources.opening_stock_wms,
        "product_code",
        [product_code],
    )

    if opening_rows.empty:
        if sources.opening_absent_means_zero:
            return OpeningStockResolution(
                value=0.0,
                warning=(
                    f"Produsul {product_code} nu a fost găsit în stocul inițial WMS; "
                    "politica explicită opening_absent_means_zero=True îl tratează ca 0."
                ),
                details={
                    "opening_absent_means_zero": True,
                    "product_absent": True,
                    "applied_value": 0.0,
                },
            )
        return OpeningStockResolution(
            value=None,
            warning=(
                f"Produsul {product_code} nu a fost găsit în stocul inițial WMS."
            ),
            details={
                "opening_absent_means_zero": False,
                "product_absent": True,
                "applied_value": None,
            },
        )

    value = round(
        numeric_sum(opening_rows, "initial_stock"),
        decimals,
    )
    return OpeningStockResolution(
        value=value,
        warning=None,
        details={
            "opening_absent_means_zero": sources.opening_absent_means_zero,
            "product_absent": False,
            "applied_value": value,
        },
    )

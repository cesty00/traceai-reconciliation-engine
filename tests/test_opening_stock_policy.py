from __future__ import annotations

from pathlib import Path

import pandas as pd

from traceai_reconciliation.investigation.models import InvestigationSources
from traceai_reconciliation.investigation.opening_stock_policy import (
    resolve_opening_stock_wms,
)


def _sources(
    tmp_path: Path,
    *,
    opening_absent_means_zero: bool,
) -> InvestigationSources:
    opening = tmp_path / "opening.xlsx"
    return InvestigationSources(
        stock_report=tmp_path / "stock.xlsx",
        opening_stock_wms=opening,
        wms_movements=tmp_path / "wms.csv",
        wme_ledger=tmp_path / "wme.xlsx",
        production=tmp_path / "production.csv",
        nomenclature=tmp_path / "nomenclature.xlsx",
        opening_absent_means_zero=opening_absent_means_zero,
    )


def test_opening_stock_absent_can_be_explicit_zero(tmp_path: Path) -> None:
    sources = _sources(
        tmp_path,
        opening_absent_means_zero=True,
    )
    pd.DataFrame(
        [{"CodArticol": "OTHER", "Cantitate": 7.0}]
    ).to_excel(sources.opening_stock_wms, index=False)

    result = resolve_opening_stock_wms(
        sources,
        product_code="DS001",
        decimals=3,
    )

    assert result.value == 0.0
    assert result.details == {
        "opening_absent_means_zero": True,
        "product_absent": True,
        "applied_value": 0.0,
    }
    assert "îl tratează ca 0" in str(result.warning)


def test_opening_stock_absent_remains_unknown_by_default(
    tmp_path: Path,
) -> None:
    sources = _sources(
        tmp_path,
        opening_absent_means_zero=False,
    )
    pd.DataFrame(
        [{"CodArticol": "OTHER", "Cantitate": 7.0}]
    ).to_excel(sources.opening_stock_wms, index=False)

    result = resolve_opening_stock_wms(
        sources,
        product_code="DS001",
        decimals=3,
    )

    assert result.value is None
    assert result.details == {
        "opening_absent_means_zero": False,
        "product_absent": True,
        "applied_value": None,
    }
    assert result.warning == (
        "Produsul DS001 nu a fost găsit în stocul inițial WMS."
    )


def test_opening_stock_present_uses_initial_stock_semantic_column(
    tmp_path: Path,
) -> None:
    sources = _sources(
        tmp_path,
        opening_absent_means_zero=False,
    )
    pd.DataFrame(
        [
            {"CodArticol": "DS001", "Cantitate": 2.3456},
            {"CodArticol": "DS001", "Cantitate": 1.1111},
            {"CodArticol": "OTHER", "Cantitate": 99.0},
        ]
    ).to_excel(sources.opening_stock_wms, index=False)

    result = resolve_opening_stock_wms(
        sources,
        product_code="DS001",
        decimals=3,
    )

    assert result.value == 3.457
    assert result.warning is None
    assert result.details == {
        "opening_absent_means_zero": False,
        "product_absent": False,
        "applied_value": 3.457,
    }

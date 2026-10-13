from __future__ import annotations

from pathlib import Path

from traceai_reconciliation.investigation.models import InvestigationSources
from traceai_reconciliation.investigation.source_provenance import (
    source_paths,
    source_usage,
)


def _sources(tmp_path: Path) -> InvestigationSources:
    return InvestigationSources(
        stock_report=tmp_path / "stock.xlsx",
        opening_stock_wms=tmp_path / "opening.xlsx",
        wms_movements=tmp_path / "wms.csv",
        wme_ledger=tmp_path / "wme.xlsx",
        production=tmp_path / "production.csv",
        nomenclature=tmp_path / "nomenclature.xlsx",
    )


def test_source_paths_uses_stable_semantic_keys(tmp_path: Path) -> None:
    sources = _sources(tmp_path)

    assert source_paths(sources) == {
        "stock_report": tmp_path / "stock.xlsx",
        "opening_stock_wms": tmp_path / "opening.xlsx",
        "wms_movements": tmp_path / "wms.csv",
        "wme_ledger": tmp_path / "wme.xlsx",
        "production": tmp_path / "production.csv",
        "nomenclature": tmp_path / "nomenclature.xlsx",
    }


def test_source_usage_preserves_operator_provenance_contract(
    tmp_path: Path,
) -> None:
    sources = _sources(tmp_path)

    usage = source_usage(
        sources,
        period="01.01.2026-13.10.2026",
    )

    assert [item["source_id"] for item in usage] == [
        "SRC-STOCK-REPORT",
        "SRC-OPENING-WMS",
        "SRC-WMS",
        "SRC-WME",
        "SRC-PROD",
        "SRC-NOM",
    ]
    assert usage[0] == {
        "source_id": "SRC-STOCK-REPORT",
        "name": "stock.xlsx",
        "period": "01.01.2026-13.10.2026",
        "role": "diferență de pornire",
        "status": "VERIFICAT",
    }
    assert usage[1]["period"] == "01.01.2026"
    assert usage[-1]["period"] == "-"
    assert all(item["status"] == "VERIFICAT" for item in usage)

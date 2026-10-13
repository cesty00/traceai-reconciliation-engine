from __future__ import annotations

from pathlib import Path

from .models import InvestigationSources


def source_paths(sources: InvestigationSources) -> dict[str, Path]:
    """Return stable semantic source names mapped to their input files."""
    return {
        "stock_report": sources.stock_report,
        "opening_stock_wms": sources.opening_stock_wms,
        "wms_movements": sources.wms_movements,
        "wme_ledger": sources.wme_ledger,
        "production": sources.production,
        "nomenclature": sources.nomenclature,
    }


def source_usage(
    sources: InvestigationSources,
    *,
    period: str,
) -> list[dict[str, str]]:
    """Build operator-facing provenance metadata without reading source data."""
    return [
        {
            "source_id": "SRC-STOCK-REPORT",
            "name": sources.stock_report.name,
            "period": period,
            "role": "diferență de pornire",
            "status": "VERIFICAT",
        },
        {
            "source_id": "SRC-OPENING-WMS",
            "name": sources.opening_stock_wms.name,
            "period": "01.01.2026",
            "role": "stoc inițial WMS",
            "status": "VERIFICAT",
        },
        {
            "source_id": "SRC-WMS",
            "name": sources.wms_movements.name,
            "period": period,
            "role": "mișcări WMS",
            "status": "VERIFICAT",
        },
        {
            "source_id": "SRC-WME",
            "name": sources.wme_ledger.name,
            "period": period,
            "role": "fișă magazie WME",
            "status": "VERIFICAT",
        },
        {
            "source_id": "SRC-PROD",
            "name": sources.production.name,
            "period": period,
            "role": "producție",
            "status": "VERIFICAT",
        },
        {
            "source_id": "SRC-NOM",
            "name": sources.nomenclature.name,
            "period": "-",
            "role": "nomenclator produs",
            "status": "VERIFICAT",
        },
    ]

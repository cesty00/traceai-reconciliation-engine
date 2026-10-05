from __future__ import annotations

from pathlib import Path

import pandas as pd

from traceai_reconciliation.investigation import (
    InvestigationSources,
    build_case_report,
    investigate_product,
)
from traceai_reconciliation.reports import validate_case_report


def _write_fixture_sources(tmp_path: Path) -> InvestigationSources:
    stock_report = tmp_path / "stock_report.xlsx"
    opening = tmp_path / "opening.xlsx"
    wms = tmp_path / "wms.csv"
    wme = tmp_path / "wme.xlsx"
    production = tmp_path / "production.csv"
    nomenclature = tmp_path / "nomenclature.xlsx"

    pd.DataFrame(
        [
            {
                "CodArticol": "DS001",
                "DenumireArticol": "Produs test",
                "QuantityERP": 8.0,
                "QuantityWMS": 10.0,
                "QuantityDifference": 2.0,
                "Gestiune": "Depozitare",
            }
        ]
    ).to_excel(stock_report, index=False)

    pd.DataFrame(
        [{"CodArticol": "DS001", "Cantitate": 5.0}]
    ).to_excel(opening, index=False)

    pd.DataFrame(
        [
            {
                "Data": "2026-01-02",
                "CodArticol": "DS001",
                "Tip operatiune": "Receptie",
                "Document": "IN1",
                "Cantitate": 5.0,
                "Gestiune": "Depozitare",
            },
            {
                "Data": "2026-01-03",
                "CodArticol": "OTHER",
                "Tip operatiune": "Livrare",
                "Document": "OUT1",
                "Cantitate": -1.0,
                "Gestiune": "Depozitare",
            },
        ]
    ).to_csv(wms, index=False)

    pd.DataFrame(
        [
            {
                "ID articol": "1001",
                "Data": "2026-01-02",
                "Tip document": "F",
                "Nr document": "IN1",
                "Cantitate": 5.0,
                "Stoc": 8.0,
            },
            {
                "ID articol": "9999",
                "Data": "2026-01-02",
                "Tip document": "F",
                "Nr document": "X",
                "Cantitate": 1.0,
                "Stoc": 1.0,
            },
        ]
    ).to_excel(wme, index=False)

    pd.DataFrame(
        [
            {
                "Data": "2026-01-04",
                "Cod produs": "DS001",
                "Tip": "PREDARE",
                "Numar Comanda": "P1",
                "Cantitate": 1.0,
            }
        ]
    ).to_csv(production, index=False)

    pd.DataFrame(
        [
            {
                "ID articol WME": "1001",
                "Cod produs WMS/DS": "DS001",
                "Denumire articol": "Produs test",
            }
        ]
    ).to_excel(nomenclature, index=False)

    return InvestigationSources(
        stock_report=stock_report,
        opening_stock_wms=opening,
        wms_movements=wms,
        wme_ledger=wme,
        production=production,
        nomenclature=nomenclature,
    )


def test_real_product_pipeline_builds_case_report(tmp_path: Path) -> None:
    sources = _write_fixture_sources(tmp_path)

    result = investigate_product(
        product_code="DS001",
        case_id="CASE-2026-TEST001",
        sources=sources,
        period="01.01.2026-04.10.2026",
        report_date="05.10.2026",
    )

    assert result.product_code == "DS001"
    assert result.initial_difference == 2.0
    assert result.details["wms_rows"] == 1
    assert result.details["wme_rows"] == 1
    assert result.details["production_rows"] == 1
    assert result.details["wme_mapping_ids"] == ["1001"]
    assert len(result.operation_timeline) == 3

    report = build_case_report(
        result,
        engine_version="0.3.0",
        engine_commit_sha="TEST",
        rules_version="0.1",
        execution_id="RUN-TEST",
    )

    assert report.engine_version == "0.3.0"
    assert report.initial_difference == 2.0
    assert report.unexplained_difference == 2.0
    assert validate_case_report(report) == []


def test_missing_wme_mapping_remains_review(tmp_path: Path) -> None:
    sources = _write_fixture_sources(tmp_path)
    pd.DataFrame(
        [{"ID articol WME": "2000", "Cod produs WMS/DS": "OTHER"}]
    ).to_excel(sources.nomenclature, index=False)

    result = investigate_product(
        product_code="DS001",
        case_id="CASE-2026-TEST002",
        sources=sources,
        period="01.01.2026-04.10.2026",
        report_date="05.10.2026",
    )

    assert result.verdict == "REVIEW"
    assert result.cause_code == "CAUSE-MASTER-DATA"
    assert result.cause_status == "PROBABILA"
    assert result.evidence_level == "C"
    assert result.details["wme_rows"] == 0

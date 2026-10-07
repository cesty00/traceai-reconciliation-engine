from __future__ import annotations

from pathlib import Path

import pandas as pd

from traceai_reconciliation.investigation import (
    InvestigationSources,
    build_case_report,
    investigate_product,
)
from traceai_reconciliation.reports import validate_case_report
from traceai_reconciliation.investigation.engine import (
    _wme_balance_total_at,
    _wme_final_balances,
)


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

    # WME real export is a report-style workbook without an operational header.
    wme_rows = [
        ["Oceanis Seafood Europa S.R.L."] + [None] * 16,
        ["Fisa de magazie"] + [None] * 16,
        [
            1, "F", "IN1", "02.01.2026", 5.0, 0.0, 8.0, 0.0,
            "345", "FURNIZOR TEST", "Produs test", "", 1001,
            "DEPOZIT PESTE PROASPAT", "BUC", "TEST", 1,
        ],
        [
            2, "F", "X", "02.01.2026", 1.0, 0.0, 1.0, 0.0,
            "345", "FURNIZOR TEST", "Alt produs", "", 9999,
            "DEPOZIT PESTE PROASPAT", "BUC", "TEST", 2,
        ],
    ]
    pd.DataFrame(wme_rows).to_excel(wme, index=False, header=False)

    pd.DataFrame(
        [
            {
                "TipLinie": "PREDARE",
                "Numar Comanda": "P1",
                "Data Start": "04/01/2026 08:00:00",
                "PRE_Cod Articol": "DS001",
                "PRE_Cantitate Predare": 1.0,
                "PRE_U.M.": "BUCATA",
                "CON_Cod Articol": None,
                "CON_Cantitate Consumata": None,
                "CON_U.M.": None,
                "Utilaj Productie": "ULMA",
            }
        ]
    ).to_csv(production, index=False)

    pd.DataFrame(
        [
            {
                "Cod articol": "DS001",
                "Denumire": "Produs test",
                "Greutate:": 1,
                "U.M.": "BUCATA",
                "Bucati in Bax": 0,
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
    # Make the WME product name non-matching so exact-name mapping cannot be established.
    wme_rows = [
        ["Oceanis Seafood Europa S.R.L."] + [None] * 16,
        [
            1, "F", "IN1", "02.01.2026", 5.0, 0.0, 8.0, 0.0,
            "345", "FURNIZOR TEST", "Alt produs", "", 2000,
            "DEPOZIT PESTE PROASPAT", "BUC", "TEST", 1,
        ],
    ]
    pd.DataFrame(wme_rows).to_excel(sources.wme_ledger, index=False, header=False)

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



def test_component_math_keeps_opening_difference_separate() -> None:
    # Regression math from the first real-case pattern, without RAW data.
    initial_difference = -1419.0
    opening_difference = -17.0
    production_residual = -768.0
    delivery_residual = -16.0
    special_status_residual = -618.0

    period_explained = (
        production_residual
        + delivery_residual
        + special_status_residual
    )
    unexplained = initial_difference - period_explained

    assert period_explained == -1402.0
    assert unexplained == opening_difference
    assert initial_difference == period_explained + unexplained



def test_second_real_case_pattern_keeps_only_opening_difference_unexplained() -> None:
    # Regression math from DS099904230 pattern, without business RAW.
    final_difference = -617.0
    opening_difference = -9.0
    production_residual = -600.0
    generic_stock_correction = -8.0

    period_explained = production_residual + generic_stock_correction
    unexplained = final_difference - period_explained

    assert period_explained == -608.0
    assert unexplained == opening_difference
    assert final_difference == period_explained + unexplained



def test_third_real_case_pattern_keeps_unlinked_wme_residual_unexplained() -> None:
    # Regression math from DS099904370 pattern, without business RAW.
    final_difference = -935.0
    production_residual = -934.0
    delivery_residual = -0.5
    unlinked_wme_residual_effect = -0.5

    explained = production_residual + delivery_residual
    unexplained = final_difference - explained

    assert explained == -934.5
    assert unexplained == -0.5
    assert unlinked_wme_residual_effect == -0.5
    # WME residual evidence is intentionally not auto-added to explained.



def test_wme_balances_preserve_multiple_accounts_in_same_warehouse() -> None:
    rows = pd.DataFrame(
        [
            {
                "LineNo": 1,
                "Date": "31.12.2025",
                "Balance": 4.3,
                "Account": "301",
                "Warehouse": "SECTIE PRODUCTIE",
            },
            {
                "LineNo": 2,
                "Date": "31.12.2025",
                "Balance": 14.549,
                "Account": "345",
                "Warehouse": "SECTIE PRODUCTIE",
            },
            {
                "LineNo": 3,
                "Date": "31.12.2025",
                "Balance": 16.793,
                "Account": "345",
                "Warehouse": "DEPOZIT PESTE PROASPAT",
            },
        ]
    )

    by_warehouse, total = _wme_final_balances(rows)
    at_cutoff, cutoff_total = _wme_balance_total_at(
        rows,
        pd.Timestamp("2026-01-01"),
        strictly_before=True,
    )

    assert by_warehouse["SECTIE PRODUCTIE"] == 18.849
    assert by_warehouse["DEPOZIT PESTE PROASPAT"] == 16.793
    assert total == 35.642

    assert at_cutoff["SECTIE PRODUCTIE"] == 18.849
    assert at_cutoff["DEPOZIT PESTE PROASPAT"] == 16.793
    assert cutoff_total == 35.642

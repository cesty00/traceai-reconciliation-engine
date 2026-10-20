"""GOV-002M: real investigate_product entrypoint with synthetic file exports.

This checks a safe unresolved case end-to-end. It does NOT certify cross-matcher
economic ownership (GOV-AT-05/06 remain open).
"""
import hashlib

import pandas as pd

from traceai_reconciliation.investigation import InvestigationSources, investigate_product


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gov_002m_unresolved_synthetic_case_keeps_balance_and_original_files(tmp_path):
    stock = tmp_path / "stock.xlsx"
    opening = tmp_path / "opening.xlsx"
    wms = tmp_path / "wms.csv"
    wme = tmp_path / "wme.xlsx"
    production = tmp_path / "production.csv"
    nomenclature = tmp_path / "nomenclature.xlsx"

    pd.DataFrame([{
        "CodArticol": "SYN001", "DenumireArticol": "Synthetic SKU",
        "QuantityERP": 8.0, "QuantityWMS": 10.0,
        "QuantityDifference": 2.0, "Gestiune": "Depozitare",
    }]).to_excel(stock, index=False)
    pd.DataFrame([{"CodArticol": "SYN001", "Cantitate": 5.0}]).to_excel(opening, index=False)
    pd.DataFrame([{
        "Data": "2026-01-02", "CodArticol": "SYN001",
        "Tip operatiune": "Receptie", "Document": "IN1",
        "Cantitate": 5.0, "Gestiune": "Depozitare",
    }]).to_csv(wms, index=False)

    # WME report-style XLSX: 2 title lines, then a genuine physical data row 3.
    pd.DataFrame([
        ["Synthetic exporter"] + [None] * 16,
        ["Fisa de magazie"] + [None] * 16,
        [1, "F", "IN1", "02.01.2026", 5.0, 0.0, 8.0, 0.0,
         "345", "SYNTHETIC", "Synthetic SKU", "", 1001,
         "DEPOZIT PESTE PROASPAT", "BUC", "TEST", 1],
    ]).to_excel(wme, index=False, header=False)
    pd.DataFrame([{
        "TipLinie": "PREDARE", "Numar Comanda": "P1",
        "Data Start": "04/01/2026 08:00:00",
        "PRE_Cod Articol": "SYN001", "PRE_Cantitate Predare": 1.0,
        "PRE_U.M.": "BUCATA", "CON_Cod Articol": None,
        "CON_Cantitate Consumata": None, "CON_U.M.": None,
        "Utilaj Productie": "ULMA",
    }]).to_csv(production, index=False)
    pd.DataFrame([{
        "Cod articol": "SYN001", "Denumire": "Synthetic SKU",
        "Greutate:": 1, "U.M.": "BUCATA", "Bucati in Bax": 0,
    }]).to_excel(nomenclature, index=False)

    files = [stock, opening, wms, wme, production, nomenclature]
    before = {p.name: _sha(p) for p in files}
    sources = InvestigationSources(
        stock_report=stock, opening_stock_wms=opening, wms_movements=wms,
        wme_ledger=wme, production=production, nomenclature=nomenclature,
    )
    result = investigate_product(
        product_code="SYN001", case_id="GOV-002M-SYNTHETIC",
        sources=sources, period="01.01.2026-04.10.2026",
        report_date="05.10.2026",
    )

    assert result.initial_difference == 2.0
    assert result.explained_difference == 0.0
    assert result.unexplained_difference == 2.0
    assert result.verdict == "REVIEW"
    assert result.details["wms_rows"] == 1
    assert result.details["wme_rows"] == 1
    assert result.details["wme_mapping_ids"] == ["1001"]
    assert len(result.operation_timeline) == 3
    assert result.initial_difference == (
        result.explained_difference + result.unexplained_difference
    )
    assert {p.name: _sha(p) for p in files} == before

"""GOV-002O: file-backed inventory PV overlap through investigate_product.

All files are synthetic. This covers a specific CORE orchestration path; it
does not establish global event ownership across all matchers.
"""
from __future__ import annotations

import hashlib

import pandas as pd

from traceai_reconciliation.investigation import InvestigationSources, investigate_product


def test_gov_002o_file_backed_pv_mismatch_remains_review_without_double_explanation(tmp_path):
    stock = tmp_path / "stock.xlsx"
    opening = tmp_path / "opening.xlsx"
    wms = tmp_path / "wms.csv"
    wme = tmp_path / "wme.xlsx"
    production = tmp_path / "production.csv"
    nomenclature = tmp_path / "nomenclature.xlsx"
    pd.DataFrame([{
        "CodArticol": "SYN-PV",
        "DenumireArticol": "Synthetic inventory product",
        "QuantityERP": 8.0,
        "QuantityWMS": 7.0,
        "QuantityDifference": -1.0,
        "Gestiune": "Depozitare",
    }]).to_excel(stock, index=False)
    pd.DataFrame([{"CodArticol": "SYN-PV", "Cantitate": 17.0}]).to_excel(opening, index=False)
    pd.DataFrame([{
        "Data": "2026-01-05",
        "CodArticol": "SYN-PV",
        "Tip operatiune": "Ajustare negativa",
        "Cantitate": -10.0,
        "Cod-motiv": "INV-MIN",
        "Document": "INV-SYN-1",
        "Numar comanda": "",
        "Locatie sursa": "A-01",
        "Gestiune": "Depozitare",
    }]).to_csv(wms, index=False)
    pd.DataFrame([
        ["Synthetic exporter"] + [None] * 16,
        ["Fisa de magazie"] + [None] * 16,
        [1, "PV", "PV-SYN-1", "05.01.2026", 0.0, 9.0, 8.0, 0.0,
         "345", "SYNTHETIC", "Synthetic inventory product", "", 1001,
         "DEPOZIT PESTE PROASPAT", "BUC", "TEST", 1],
    ]).to_excel(wme, index=False, header=False)
    pd.DataFrame([{
        "TipLinie": "PREDARE", "Numar Comanda": "UNRELATED",
        "Data Start": "04/01/2026 08:00:00",
        "PRE_Cod Articol": "OTHER",
        "PRE_Cantitate Predare": 1.0,
        "PRE_U.M.": "BUCATA",
        "CON_Cod Articol": None, "CON_Cantitate Consumata": None,
        "CON_U.M.": None, "Utilaj Productie": "ULMA",
    }]).to_csv(production, index=False)
    pd.DataFrame([{
        "Cod articol": "SYN-PV",
        "Denumire": "Synthetic inventory product",
        "Greutate:": 1, "U.M.": "BUCATA", "Bucati in Bax": 0,
    }]).to_excel(nomenclature, index=False)

    paths = (stock, opening, wms, wme, production, nomenclature)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    sources = InvestigationSources(
        stock_report=stock, opening_stock_wms=opening,
        wms_movements=wms, wme_ledger=wme,
        production=production, nomenclature=nomenclature,
    )
    result = investigate_product(
        product_code="SYN-PV", case_id="GOV-002O-SYN",
        sources=sources, period="01.01.2026-04.10.2026",
        report_date="05.10.2026",
    )
    inventory = result.details["inventory_adjustment_matching"]
    residual = result.details["wme_residual_movements"]
    assert result.initial_difference == -1.0
    assert inventory["matches"] == []
    assert inventory["system_difference_effect"] == -1.0
    assert residual["residual_movements"] == 1
    assert residual["system_difference_effect"] == 9.0
    assert residual["movements"][0]["status"] == "WME_ONLY_REVIEW"
    assert result.verdict == "REVIEW"
    assert result.initial_difference == (
        result.explained_difference + result.unexplained_difference
    )
    assert result.explained_difference == -1.0
    assert all(
        hashlib.sha256(p.read_bytes()).hexdigest() == hashes[p.name] for p in paths
    )

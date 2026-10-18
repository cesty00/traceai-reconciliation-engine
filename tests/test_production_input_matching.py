from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.production_input_matching import (
    match_production_inputs,
)


def test_production_in_matches_bc_by_document() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -72.0,
                "Numar comanda": "0024212_DC",
                "Cod-motiv": "PRODUCTION-IN",
            },
            {
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -48.0,
                "Numar comanda": "0024243_DC",
                "Cod-motiv": "PRODUCTION-IN",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "BC",
                "Document": "24212",
                "SignedQuantity": -72.0,
            },
            {
                "OperationType": "BC",
                "Document": "24243",
                "SignedQuantity": -48.0,
            },
        ]
    )

    result = match_production_inputs(wms, wme)

    assert result.wms_total == -120.0
    assert result.wme_bc_total == -120.0
    assert result.residual_total == 0.0
    assert result.residual_documents == []
    assert all(item["status"] == "MATCH" for item in result.documents)


def test_production_in_quantity_difference_remains_review() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -16.0,
                "Numar comanda": "0030356_DC",
                "Cod-motiv": "PRODUCTION-IN",
            }
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "BC",
                "Document": "30356",
                "SignedQuantity": -8.0,
            }
        ]
    )

    result = match_production_inputs(wms, wme)

    assert result.residual_total == -8.0
    assert len(result.residual_documents) == 1
    item = result.residual_documents[0]
    assert item["document"] == "30356"
    assert item["wms_production_in"] == -16.0
    assert item["wme_bc"] == -8.0
    assert item["difference"] == -8.0
    assert item["residual_kind"] == "WME_BC_QTY_DIFF"
    assert item["status"] == "QTY_DIFF"
    assert item["first_date"] is None
    assert item["last_date"] is None
    assert item["production_confirmed"] is False
    assert item["fully_reversed"] is False
    assert item["wms_reversal"] == 0.0
    assert item["wms_effective"] == -16.0
    assert item["production_consumption"] == 0.0
    return


def test_production_in_missing_bc_is_confirmed_by_production_report() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -428.4,
                "Numar comanda": "0034904_DC",
                "Cod-motiv": "PRODUCTION-IN",
            }
        ]
    )
    wme = pd.DataFrame(columns=["OperationType", "Document", "SignedQuantity"])
    production = pd.DataFrame(
        [
            {
                "TipLinie": "CONSUM",
                "Numar Comanda": "0034904_DC",
                "CON_Cantitate Consumata": 428.4,
            }
        ]
    )

    result = match_production_inputs(
        wms,
        wme,
        production_rows=production,
    )

    assert result.residual_total == -428.4
    assert len(result.residual_documents) == 1
    item = result.residual_documents[0]
    assert item["document"] == "34904"
    assert item["wms_production_in"] == -428.4
    assert item["wme_bc"] == 0.0
    assert item["production_consumption"] == 428.4
    assert item["production_confirmed"] is True
    assert item["residual_kind"] == "WME_BC_MISSING"
    assert item["difference"] == -428.4
    assert item["status"] == "QTY_DIFF"
    return


def test_production_in_explicit_cor_stoc_reversal_is_not_missing_bc() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -1.0,
                "Numar comanda": "0037112_AE",
                "Cod-motiv": "PRODUCTION-IN",
                "Detalii": "Order production number: 0037112_AE",
            },
            {
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 1.0,
                "Numar comanda": None,
                "Cod-motiv": "COR STOC",
                "Detalii": "CONSUM ERONAT COMANDA 37112",
            },
        ]
    )
    wme = pd.DataFrame(columns=["OperationType", "Document", "SignedQuantity"])
    production = pd.DataFrame(
        [
            {
                "TipLinie": "CONSUM",
                "Numar Comanda": "0037112_AE",
                "CON_Cantitate Consumata": 1.0,
            }
        ]
    )

    result = match_production_inputs(
        wms,
        wme,
        production_rows=production,
    )

    assert result.residual_total == 0.0
    assert result.residual_documents == []
    assert len(result.reversed_documents or []) == 1
    item = result.documents[0]
    assert item["document"] == "37112"
    assert item["wms_production_in"] == -1.0
    assert item["wms_reversal"] == 1.0
    assert item["wms_effective"] == 0.0
    assert item["fully_reversed"] is True
    assert item["residual_kind"] == "WMS_PRODUCTION_IN_REVERSED"
    assert item["status"] == "REVERSED"


def test_cor_stoc_reference_for_other_order_does_not_cancel_production_in() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -1.0,
                "Numar comanda": "0037112_AE",
                "Cod-motiv": "PRODUCTION-IN",
                "Detalii": "Order production number: 0037112_AE",
            },
            {
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 1.0,
                "Numar comanda": None,
                "Cod-motiv": "COR STOC",
                "Detalii": "CONSUM ERONAT COMANDA 37126",
            },
        ]
    )
    wme = pd.DataFrame(columns=["OperationType", "Document", "SignedQuantity"])

    result = match_production_inputs(wms, wme)

    assert result.residual_total == -1.0
    assert len(result.residual_documents) == 1
    assert result.residual_documents[0]["residual_kind"] == "WME_BC_MISSING"



def test_prod03_inventory_checkpoint_alone_does_not_neutralize_bc_residual() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "27/03/2026 13:29:44",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -17.0,
                "Numar comanda": "0029279_DC",
                "Cod-motiv": "PRODUCTION-IN",
                "Detalii": "Order production number: 0029279_DC",
            },
            {
                "Data": "07/06/2026 15:18:59",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 100.0,
                "Numar comanda": None,
                "Cod-motiv": "COR STOC",
                "Detalii": "corectie stoc fizic inventar sp",
            },
        ]
    )
    wme = pd.DataFrame(columns=["OperationType", "Document", "SignedQuantity"])
    production = pd.DataFrame(
        [
            {
                "TipLinie": "CONSUM",
                "Numar Comanda": "0029279_DC",
                "CON_Cantitate Consumata": 17.0,
            }
        ]
    )

    result = match_production_inputs(wms, wme, production_rows=production)

    assert result.residual_total == -17.0
    assert result.persistent_residual_total == -17.0
    assert len(result.neutralized_residual_documents or []) == 0
    assert len(result.persistent_residual_documents or []) == 1
    assert result.persistent_residual_documents[0]["persistence_status"] == "PERSISTENT"
    assert result.inventory_checkpoint_date is not None


def test_prod03_explicit_later_cor_stoc_neutralizes_residual() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "11/09/2026 17:43:42",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -1008.0,
                "Numar comanda": "0038457_DC",
                "Cod-motiv": "PRODUCTION-IN",
                "Detalii": "Order production number: 0038457_DC",
            },
            {
                "Data": "14/09/2026 07:41:33",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -554.4,
                "Numar comanda": None,
                "Cod-motiv": "COR STOC",
                "Detalii": "COMANDA PRODUCTIE 38457",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "BC",
                "Document": "38457",
                "SignedQuantity": -1562.4,
            }
        ]
    )
    production = pd.DataFrame(
        [
            {
                "TipLinie": "CONSUM",
                "Numar Comanda": "0038457_DC",
                "CON_Cantitate Consumata": 1008.0,
            }
        ]
    )

    result = match_production_inputs(wms, wme, production_rows=production)

    assert round(result.residual_total, 3) == 554.4
    assert result.persistent_residual_total == 0.0
    assert result.safe_to_auto_explain is False
    assert len(result.neutralized_residual_documents or []) == 1
    item = result.neutralized_residual_documents[0]
    assert item["persistence_status"] == "EXPLICIT_COR_STOC_NEUTRALIZATION"
    assert item["neutralizing_correction"]["quantity"] == -554.4


def test_prod03_split_bc_basket_preserves_only_other_order_consumption() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "15/09/2026 14:00:24",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -23.23,
                "Numar comanda": "0038644_AE",
                "Cod-motiv": "PRODUCTION-IN",
                "Detalii": "Order production number: 0038644_AE",
            },
            {
                "Data": "16/09/2026 00:04:00",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -1.0,
                "Numar comanda": "0038688_AE",
                "Cod-motiv": "PRODUCTION-IN",
                "Detalii": "Order production number: 0038688_AE",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "BC",
                "Document": "38644",
                "SignedQuantity": -5.625,
            },
            {
                "OperationType": "BC",
                "Document": "38688",
                "SignedQuantity": -17.605,
            },
        ]
    )
    production = pd.DataFrame(
        [
            {
                "TipLinie": "CONSUM",
                "Numar Comanda": "0038644_AE",
                "CON_Cantitate Consumata": 23.23,
            },
            {
                "TipLinie": "CONSUM",
                "Numar Comanda": "0038688_AE",
                "CON_Cantitate Consumata": 1.0,
            },
        ]
    )

    result = match_production_inputs(wms, wme, production_rows=production)

    assert round(result.residual_total, 3) == -1.0
    assert round(result.persistent_residual_total, 3) == -1.0
    assert result.safe_to_auto_explain is True
    assert len(result.basket_groups or []) == 1
    basket = result.basket_groups[0]
    assert basket["documents"] == ["38644", "38688"]
    assert round(basket["wme_basket"], 3) == -23.23
    assert round(basket["persistent_effect"], 3) == -1.0

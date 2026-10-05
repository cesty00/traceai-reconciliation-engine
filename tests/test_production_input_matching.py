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
    assert result.residual_documents == [
        {
            "document": "30356",
            "wms_production_in": -16.0,
            "wme_bc": -8.0,
            "production_consumption": 0.0,
            "production_confirmed": False,
            "residual_kind": "WME_BC_QTY_DIFF",
            "difference": -8.0,
            "status": "QTY_DIFF",
        }
    ]


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
    assert result.residual_documents == [
        {
            "document": "34904",
            "wms_production_in": -428.4,
            "wme_bc": 0.0,
            "production_consumption": 428.4,
            "production_confirmed": True,
            "residual_kind": "WME_BC_MISSING",
            "difference": -428.4,
            "status": "QTY_DIFF",
        }
    ]

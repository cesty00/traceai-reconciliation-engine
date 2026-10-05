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
            "difference": -8.0,
            "status": "QTY_DIFF",
        }
    ]

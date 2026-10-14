"""Regression: production BC quantities are compared 1:1, independent of inventory checkpoints."""
import pandas as pd

from traceai_reconciliation.investigation.production_input_matching import match_production_inputs
from traceai_reconciliation.investigation.production_matching import normalize_document


def test_order_normalization_and_quantity_mismatch_survives_inventory():
    assert normalize_document("0023448_DC") == "23448"
    assert normalize_document("0023454_AE") == "23454"

    wms = pd.DataFrame([
        {
            "Tip operatiune": "Ajustare negativa",
            "Cod-motiv": "PRODUCTION-IN",
            "Numar comanda": "0023448_DC",
            "Cantitate": -720,
            "Data": "02.01.2026",
            "Detalii": "",
        },
        {
            "Tip operatiune": "Ajustare negativa",
            "Cod-motiv": "COR STOC",
            "Numar comanda": "",
            "Cantitate": -1,
            "Data": "05.06.2026",
            "Detalii": "INVENTAR 05.06.2026",
        },
    ])
    wme = pd.DataFrame([
        {"OperationType": "BC", "Document": "23448", "SignedQuantity": -90},
    ])
    result = match_production_inputs(wms, wme)
    assert result.documents[0]["difference"] == -630
    assert result.documents[0]["status"] == "QTY_DIFF"
    assert len(result.persistent_residual_documents) == 1
    assert len(result.neutralized_residual_documents) == 0


def test_nearby_order_number_does_not_neutralize_bc_difference():
    wms = pd.DataFrame([
        {
            "Tip operatiune": "Ajustare negativa",
            "Cod-motiv": "PRODUCTION-IN",
            "Numar comanda": "0023448_DC",
            "Cantitate": -720,
            "Data": "02.01.2026",
            "Detalii": "",
        },
        {
            "Tip operatiune": "Ajustare pozitiva",
            "Cod-motiv": "COR STOC",
            "Numar comanda": "",
            "Cantitate": 630,
            "Data": "03.01.2026",
            "Detalii": "revers comanda 1234480",
        },
    ])
    wme = pd.DataFrame([
        {"OperationType": "BC", "Document": "23448", "SignedQuantity": -90},
    ])
    result = match_production_inputs(wms, wme)
    assert result.documents[0]["wms_reversal"] == 0
    assert len(result.persistent_residual_documents) == 1

from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.production_matching import (
    match_production_adjustments,
    normalize_document,
)


def test_normalize_production_document() -> None:
    assert normalize_document("0031979_AE") == "31979"
    assert normalize_document("0029890_DC") == "29890"
    assert normalize_document("NP31979") == "31979"
    assert normalize_document(None) == ""


def test_wms_surplus_pair_is_classified_as_reversal() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-04-04 11:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 768.0,
                "Numar comanda": "0029890_AE",
                "Locatie sursa": "ULMA",
                "Lot": "096.26",
            },
            {
                "Data": "2026-04-04 11:00:10",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 336.0,
                "Numar comanda": "0029890_AE",
                "Locatie sursa": "ULMA",
                "Lot": "096.26",
            },
            {
                "Data": "2026-04-04 11:08:39",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -768.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "096.26",
            },
            {
                "Data": "2026-04-04 11:08:06",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -336.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "096.26",
            },
        ]
    )
    wme = pd.DataFrame(
        columns=[
            "OperationType",
            "Document",
            "SignedQuantity",
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert result.wms_positive_total == 1104.0
    assert result.wme_np_total == 0.0
    assert len(result.reversal_pairs) == 2
    assert result.residual_wms_adjustments == []
    assert result.residual_total == 0.0


def test_matched_np_positive_is_not_consumed_by_blank_negative() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-05-06 17:43:02",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 768.0,
                "Numar comanda": "0031979_AE",
                "Locatie sursa": "ULMA",
                "Lot": "127.26S1",
            },
            {
                "Data": "2026-05-06 17:43:03",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 768.0,
                "Numar comanda": "0031979_AE",
                "Locatie sursa": "ULMA",
                "Lot": "127.26S1",
            },
            {
                "Data": "2026-05-06 17:43:44",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -768.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "127.26S1",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "31979",
                "SignedQuantity": 768.0,
            },
            {
                "OperationType": "NP",
                "Document": "31979",
                "SignedQuantity": 768.0,
            },
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert result.matched_documents == [
        {
            "document": "31979",
            "wms_quantity": 1536.0,
            "wme_np_quantity": 1536.0,
            "difference": 0.0,
            "status": "MATCH",
        }
    ]
    assert result.reversal_pairs == []
    assert len(result.residual_wms_adjustments) == 1
    residual = result.residual_wms_adjustments[0]
    assert residual["quantity"] == -768.0
    assert residual["lot"] == "127.26S1"
    assert residual["location"] == "ULMA"
    assert result.residual_total == -768.0


def test_non_production_positive_adjustment_is_not_compared_to_np() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-02-05 20:18:34",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 640.0,
                "Numar comanda": "109129",
                "Locatie sursa": "INS.DPP",
                "Lot": "036.26",
                "Cod-motiv": "COR STOC",
            },
            {
                "Data": "2026-05-06 17:43:02",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 768.0,
                "Numar comanda": "0031979_AE",
                "Locatie sursa": "ULMA",
                "Lot": "127.26S1",
                "Cod-motiv": "PRODUCTION-OUT",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "31979",
                "SignedQuantity": 768.0,
            }
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert result.wms_positive_total == 768.0
    assert result.wme_np_total == 768.0
    assert all(item["document"] != "109129" for item in result.matched_documents)

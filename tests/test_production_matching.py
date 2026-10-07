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
    assert sum(
        item["quantity"] for item in result.reversal_pairs
    ) == 1104.0
    assert any(
        item["status"] in {"WMS_AGGREGATE_SCOPE_REVERSAL", "WMS_REVERSAL_PAIR"}
        for item in result.reversal_pairs
    )
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


def test_document_residual_excludes_fully_reversed_wms_only_order() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-01-23 10:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 16.0,
                "Numar comanda": "0024707_EV",
                "Locatie sursa": "ULMA",
                "Lot": "023.26",
                "Cod-motiv": "PRODUCTION-OUT",
            },
            {
                "Data": "2026-07-20 22:40:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 16.0,
                "Numar comanda": "0035666_EV",
                "Locatie sursa": "ULMA",
                "Lot": "202.26",
                "Cod-motiv": "PRODUCTION-OUT",
            },
            {
                "Data": "2026-07-20 22:47:11",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -16.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "202.26",
                "Cod-motiv": "COR STOC",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "24707",
                "SignedQuantity": 53.0,
            }
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert len(result.reversal_pairs) == 1
    assert len(result.document_residuals) == 1
    residual = result.document_residuals[0]
    assert residual["document"] == "24707"
    assert residual["raw_difference"] == -37.0
    assert residual["reversed_wms_positive"] == 0.0
    assert residual["correction_effect"] == 0.0
    assert residual["effective_difference"] == -37.0
    assert residual["status"] == "QTY_DIFF_AFTER_REVERSALS_AND_CORRECTIONS"
    assert result.document_residual_total == -37.0



def test_explicit_multirow_corrections_close_referenced_np_order() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-10-01 10:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 100.0,
                "Numar comanda": "0039655_AE",
                "Locatie sursa": "ULMA",
                "Lot": "274.26A",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-10-01 10:01:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 44.2,
                "Numar comanda": "0039655_AE",
                "Locatie sursa": "ULMA",
                "Lot": "274.26B",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-10-01 10:05:00",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -20.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "274.26A",
                "Cod-motiv": "COR STOC",
                "Detalii": "CORECTIE COMANDA 0039655",
            },
            {
                "Data": "2026-10-01 10:06:00",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -24.2,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "274.26B",
                "Cod-motiv": "COR STOC",
                "Detalii": "CORECTIE COMANDA 0039655",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "39655",
                "SignedQuantity": 100.0,
            }
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert result.document_residuals == []
    assert result.document_residual_total == 0.0
    assert result.residual_wms_adjustments == []


def test_wms_only_order_can_close_by_exact_aggregate_correction_scope() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-08-06 10:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 231.0,
                "Numar comanda": "0036576_AE",
                "Locatie sursa": "ULMA",
                "Lot": "218.26R1",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:01:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 231.0,
                "Numar comanda": "0036576_AE",
                "Locatie sursa": "ULMA",
                "Lot": "218.26F1",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:02:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 201.6,
                "Numar comanda": "0036576_AE",
                "Locatie sursa": "ULMA",
                "Lot": "218.26F3",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:03:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 231.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "218.26F1",
                "Cod-motiv": "COR STOC",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:04:00",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -462.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "218.26F1",
                "Cod-motiv": "COR STOC",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:05:00",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -231.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "218.26R1",
                "Cod-motiv": "COR STOC",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:06:00",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -201.6,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "218.26F3",
                "Cod-motiv": "COR STOC",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:10:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 663.6,
                "Numar comanda": "0036584_AE",
                "Locatie sursa": "ULMA",
                "Lot": "218.26",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "36584",
                "SignedQuantity": 663.6,
            }
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert any(
        item["positive_document_normalized"] == "36576"
        and item["status"] == "WMS_AGGREGATE_SCOPE_REVERSAL"
        for item in result.reversal_pairs
    )
    assert all(
        item["document"] != "36576"
        for item in result.document_residuals
    )


def test_unique_post_np_exact_correction_becomes_document_residual() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-02-27 14:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 202.0,
                "Numar comanda": "0027403_AE",
                "Locatie sursa": "ULMA",
                "Lot": "058.26",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-02-27 14:11:29",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -202.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "058.26",
                "Cod-motiv": "COR STOC",
                "Detalii": "PREDARE ERONATA",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "27403",
                "SignedQuantity": 202.0,
            }
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert len(result.document_residuals) == 1
    item = result.document_residuals[0]
    assert item["document"] == "27403"
    assert item["raw_difference"] == 0.0
    assert item["correction_effect"] == -202.0
    assert item["effective_difference"] == -202.0
    assert result.document_residual_total == -202.0
    assert result.residual_wms_adjustments == []


def test_wms_only_test_lot_order_is_not_numeric_residual() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-02-08 10:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 30.0,
                "Numar comanda": "0025896_AE",
                "Locatie sursa": "ULMA",
                "Lot": "TEST",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            }
        ]
    )
    wme = pd.DataFrame(
        columns=["OperationType", "Document", "SignedQuantity"]
    )

    result = match_production_adjustments(wms, wme)

    assert result.matched_documents[0]["status"] == "TEST_ORDER_IGNORED"
    assert result.document_residuals == []
    assert result.document_residual_total == 0.0


def test_ambiguous_post_np_correction_remains_review() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-02-27 14:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 202.0,
                "Numar comanda": "0027403_AE",
                "Locatie sursa": "ULMA",
                "Lot": "058.26",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-02-27 14:01:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 202.0,
                "Numar comanda": "0027405_AE",
                "Locatie sursa": "ULMA",
                "Lot": "058.26",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-02-27 14:11:29",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -202.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "058.26",
                "Cod-motiv": "COR STOC",
                "Detalii": "PREDARE ERONATA",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "27403",
                "SignedQuantity": 202.0,
            },
            {
                "OperationType": "NP",
                "Document": "27405",
                "SignedQuantity": 202.0,
            },
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert result.document_residuals == []
    assert len(result.residual_wms_adjustments) == 1
    assert result.residual_wms_adjustments[0]["quantity"] == -202.0



def test_corectie_stoc_duplicate_rows_same_document_is_unambiguous() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-05-06 17:43:02",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 768.0,
                "Numar comanda": "0031979_AE",
                "Locatie sursa": "ULMA",
                "Lot": "127.26S1",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-05-06 17:43:03",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 768.0,
                "Numar comanda": "0031979_AE",
                "Locatie sursa": "ULMA",
                "Lot": "127.26S1",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-05-06 17:43:44",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -768.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "127.26S1",
                "Cod-motiv": "CORECTIE STOC",
                "Detalii": "AJUSTARE CANTITATIVA",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {"OperationType": "NP", "Document": "31979", "SignedQuantity": 768.0},
            {"OperationType": "NP", "Document": "31979", "SignedQuantity": 768.0},
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert result.residual_wms_adjustments == []
    assert len(result.document_residuals) == 1
    item = result.document_residuals[0]
    assert item["document"] == "31979"
    assert item["raw_difference"] == 0.0
    assert item["correction_effect"] == -768.0
    assert item["effective_difference"] == -768.0


def test_test_lot_correction_is_evidence_only() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-02-08 10:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 30.0,
                "Numar comanda": "0025896_AE",
                "Locatie sursa": "ULMA",
                "Lot": "TEST",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-03-03 10:24:35",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -30.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "TEST",
                "Cod-motiv": "COR STOC",
                "Detalii": "comanda test productie",
            },
        ]
    )
    wme = pd.DataFrame(columns=["OperationType", "Document", "SignedQuantity"])

    result = match_production_adjustments(wms, wme)

    assert result.document_residuals == []
    assert result.residual_wms_adjustments == []
    assert result.residual_total == 0.0



def test_positive_unconsumed_production_location_correction_is_preserved_signed() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-08-04 10:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 100.0,
                "Numar comanda": "0036374_AE",
                "Locatie sursa": "ULMA",
                "Lot": "215.26C1",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-08-04 10:05:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 7.2,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "215.26C1",
                "Cod-motiv": "COR STOC",
                "Detalii": "EROARE PREDARE COMANDA PRODUCTIE!",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "36374",
                "SignedQuantity": 100.0,
            }
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert result.document_residual_total == 0.0
    assert result.residual_total == 0.0
    assert result.residual_wms_adjustments == []
    assert result.unconsumed_correction_total == 7.2
    assert len(result.unconsumed_correction_items) == 1
    assert result.unconsumed_correction_items[0]["quantity"] == 7.2



def test_aggregate_reversal_rejects_foreign_lot_even_if_sum_matches() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "2026-08-06 10:00:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 100.0,
                "Numar comanda": "0036576_AE",
                "Locatie sursa": "ULMA",
                "Lot": "218.26A",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:01:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 50.0,
                "Numar comanda": "0036576_AE",
                "Locatie sursa": "ULMA",
                "Lot": "218.26B",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:02:00",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -150.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Lot": "FOREIGN-LOT",
                "Cod-motiv": "COR STOC",
                "Detalii": "",
            },
            {
                "Data": "2026-08-06 10:10:00",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 10.0,
                "Numar comanda": "0036584_AE",
                "Locatie sursa": "ULMA",
                "Lot": "218.26C",
                "Cod-motiv": "PRODUCTION-OUT",
                "Detalii": "",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NP",
                "Document": "36584",
                "SignedQuantity": 10.0,
            }
        ]
    )

    result = match_production_adjustments(wms, wme)

    assert not any(
        item["positive_document_normalized"] == "36576"
        and item["status"] == "WMS_AGGREGATE_SCOPE_REVERSAL"
        for item in result.reversal_pairs
    )
    assert any(
        item["document"] == "36576"
        for item in result.document_residuals
    )
    assert any(
        item["quantity"] == -150.0
        for item in result.residual_wms_adjustments
    )

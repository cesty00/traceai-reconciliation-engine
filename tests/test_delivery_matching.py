from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.delivery_matching import (
    match_deliveries_and_returns,
    normalize_delivery_document,
)


def test_normalize_delivery_documents() -> None:
    assert normalize_delivery_document("WME108805") == "108805"
    assert normalize_delivery_document("WME108805-1") == "108805"
    assert normalize_delivery_document("WMS111828-1") == "111828"
    assert normalize_delivery_document("RET_WME109598") == "109598"
    assert normalize_delivery_document("SFA24164") == "24164"
    assert normalize_delivery_document("RET_SFA109598") == "109598"
    assert normalize_delivery_document("AV_WMS108432-1") == "108432"
    assert normalize_delivery_document("R15311") == "15311"
    assert (
        normalize_delivery_document(
            "WME108480_DEL_2EB1C6F2-A7A7-4127-8F98-9165E29BD188"
        )
        == "108480"
    )


def test_full_delivery_return_chain_nets_before_ae_comparison() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -1120.0,
                "Numar comanda": "WME109028",
            },
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 640.0,
                "Numar comanda": "WME109028-1",
            },
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 480.0,
                "Numar comanda": "WME109028-1",
            },
        ]
    )
    wme = pd.DataFrame(columns=["OperationType", "Document", "SignedQuantity"])

    result = match_deliveries_and_returns(wms, wme)

    assert result.wms_net_total == 0.0
    assert result.wme_ae_total == 0.0
    assert result.residual_total == 0.0
    assert result.residual_documents == []


def test_delivery_quantity_difference_is_residual() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -720.0,
                "Numar comanda": "WME108805",
            }
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "AE",
                "Document": "108805",
                "SignedQuantity": -712.0,
            }
        ]
    )

    result = match_deliveries_and_returns(wms, wme)

    assert result.residual_total == -8.0
    assert result.residual_documents == [
        {
            "document": "108805",
            "wms_net_quantity": -720.0,
            "wme_ae_quantity": -712.0,
            "difference": -8.0,
            "status": "QTY_DIFF",
        }
    ]


def test_ret_wme_receipt_matches_positive_ae() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 8.0,
                "Numar comanda": "RET_WME109598",
            }
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "AE",
                "Document": "109598",
                "SignedQuantity": 8.0,
            }
        ]
    )

    result = match_deliveries_and_returns(wms, wme)

    assert result.residual_total == 0.0
    assert result.residual_documents == []



def test_supplier_receipt_is_not_treated_as_delivery_return() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -100.0,
                "Numar comanda": "WME120000",
            },
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 500.0,
                "Numar comanda": "IN3969",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "AE",
                "Document": "120000",
                "SignedQuantity": -100.0,
            }
        ]
    )

    result = match_deliveries_and_returns(wms, wme)

    assert result.wms_net_total == -100.0
    assert result.wme_ae_total == -100.0
    assert result.residual_total == 0.0
    assert result.residual_documents == []



def test_transfer_delivery_is_not_compared_to_ae() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -500.0,
                "Numar comanda": "TRANSFER_MOSE-202521093",
            },
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -100.0,
                "Numar comanda": "SFA24164",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "AE",
                "Document": "24164",
                "SignedQuantity": -100.0,
            }
        ]
    )

    result = match_deliveries_and_returns(wms, wme)

    assert result.wms_net_total == -100.0
    assert result.wme_ae_total == -100.0
    assert result.residual_total == 0.0
    assert result.residual_documents == []



def test_delivery_cancellation_adjustment_nets_same_base_document() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -100.0,
                "Numar comanda": "WME115354",
                "Cod-motiv": None,
            },
            {
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 100.0,
                "Numar comanda": (
                    "115354_DEL_233B8F72-6FDE-4227-AABA-FBAA5ADE6C73"
                ),
                "Cod-motiv": "ANULARE COMANDA",
            },
        ]
    )
    wme = pd.DataFrame(
        columns=["OperationType", "Document", "SignedQuantity"]
    )

    result = match_deliveries_and_returns(wms, wme)

    assert result.wms_net_total == 0.0
    assert result.residual_total == 0.0
    assert result.residual_documents == []


def test_duplicate_delivery_plus_cancellation_matches_ae_net() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -10.0,
                "Numar comanda": "WME109254",
                "Cod-motiv": None,
            },
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -10.0,
                "Numar comanda": "WME109254",
                "Cod-motiv": None,
            },
            {
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 10.0,
                "Numar comanda": (
                    "109254_DEL_4673C091-EB3C-4A08-BB25-86C158280093"
                ),
                "Cod-motiv": "ANULARE COMANDA",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "AE",
                "Document": "109254",
                "SignedQuantity": -10.0,
            }
        ]
    )

    result = match_deliveries_and_returns(wms, wme)

    assert result.wms_net_total == -10.0
    assert result.wme_ae_total == -10.0
    assert result.residual_total == 0.0
    assert result.residual_documents == []


def test_wme_only_ae_is_reported_separately_without_changing_delivery_residual() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Livrare",
                "Cantitate": -10.0,
                "Numar comanda": "WME120000",
                "Cod-motiv": None,
            }
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "AE",
                "Document": "120000",
                "SignedQuantity": -10.0,
            },
            {
                "OperationType": "AE",
                "Document": "1025",
                "SignedQuantity": 1.0,
            },
        ]
    )

    result = match_deliveries_and_returns(wms, wme)

    assert result.residual_total == 0.0
    assert result.residual_documents == []
    assert result.wme_only_documents == [
        {
            "document": "1025",
            "wme_ae_quantity": 1.0,
            "status": "WME_ONLY_REVIEW",
        }
    ]

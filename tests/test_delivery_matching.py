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

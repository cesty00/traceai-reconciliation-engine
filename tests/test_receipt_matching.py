from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.receipt_matching import (
    match_inbound_receipts,
)


def test_supplier_in_receipt_matches_positive_fe_by_document_intrare() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 500.0,
                "Numar comanda": "IN3969",
                "Document intrare": 10546,
            },
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 497.0,
                "Numar comanda": "IN3969",
                "Document intrare": 10546,
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "FE",
                "Document": "10546",
                "SignedQuantity": 997.0,
            }
        ]
    )

    result = match_inbound_receipts(wms, wme)

    assert result.wms_supported_total == 997.0
    assert result.wme_supported_total == 997.0
    assert result.residual_total == 0.0
    assert result.residual_documents == []
    assert result.unsupported_receipts == []


def test_transfer_cg_receipt_matches_positive_nt_by_document_intrare() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 500.0,
                "Numar comanda": "TRANSFER_CG2025.30470",
                "Document intrare": 57823,
            },
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 450.0,
                "Numar comanda": "TRANSFER_CG2025.30470",
                "Document intrare": 57823,
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "NT",
                "Document": 57823,
                "SignedQuantity": 950.0,
            }
        ]
    )

    result = match_inbound_receipts(wms, wme)

    assert result.wms_supported_total == 950.0
    assert result.wme_supported_total == 950.0
    assert result.residual_total == 0.0


def test_supplier_in_quantity_difference_remains_residual() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 19997.0,
                "Numar comanda": "IN3290",
                "Document intrare": 10170,
            }
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "OperationType": "FE",
                "Document": 10170,
                "SignedQuantity": 19992.0,
            }
        ]
    )

    result = match_inbound_receipts(wms, wme)

    assert result.residual_total == 5.0
    assert result.residual_documents == [
        {
            "family": "SUPPLIER_IN",
            "document": "10170",
            "wme_operation_type": "FE",
            "wms_quantity": 19997.0,
            "wme_quantity": 19992.0,
            "difference": 5.0,
            "status": "QTY_DIFF",
        }
    ]


def test_return_and_transfer_mose_receipts_remain_outside_inbound_matcher() -> None:
    wms = pd.DataFrame(
        [
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 300.0,
                "Numar comanda": "RET_WME111037",
                "Document intrare": 111037,
            },
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 100.0,
                "Numar comanda": "TRANSFER_MOSE-202520904",
                "Document intrare": 64643,
            },
            {
                "Tip operatiune": "Receptie",
                "Cantitate": 5.0,
                "Numar comanda": "WME108432-1",
                "Document intrare": None,
            },
        ]
    )
    wme = pd.DataFrame(columns=["OperationType", "Document", "SignedQuantity"])

    result = match_inbound_receipts(wms, wme)

    assert result.documents == []
    assert result.residual_documents == []
    assert result.residual_total == 0.0
    assert len(result.unsupported_receipts) == 3

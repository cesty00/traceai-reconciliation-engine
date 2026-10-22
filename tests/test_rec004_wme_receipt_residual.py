from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.receipt_matching import match_inbound_receipts
from traceai_reconciliation.investigation.wme_residual_matching import (
    match_wme_residual_movements,
)


def _wms(qty: float = 11730.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Tip operatiune": "Receptie",
                "Cantitate": qty / 2,
                "Numar comanda": "IN3277",
                "Document intrare": "260769",
            },
            {
                "Tip operatiune": "Receptie",
                "Cantitate": qty / 2,
                "Numar comanda": "IN3277",
                "Document intrare": "260769",
            },
        ]
    )


def _wme(qty: float = 11730.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "OperationType": "F",
                "Document": "260769",
                "SignedQuantity": qty,
                "Warehouse": "DEPOZIT PRINCIPAL",
            },
            {
                "OperationType": "PV",
                "Document": "1178",
                "SignedQuantity": 160.81,
                "Warehouse": "DEPOZIT PRINCIPAL",
            },
            {
                "OperationType": "F",
                "Document": "OTHER",
                "SignedQuantity": 5.0,
                "Warehouse": "DEPOZIT PRINCIPAL",
            },
        ],
        index=[101, 102, 103],
    )


def test_rec004_matched_f_receipt_not_reported_as_wme_only() -> None:
    wme = _wme()
    receipt = match_inbound_receipts(_wms(), wme)

    assert receipt.documents == [
        {
            "family": "SUPPLIER_IN",
            "document": "260769",
            "wme_operation_type": "F",
            "wms_quantity": 11730.0,
            "wme_quantity": 11730.0,
            "difference": 0.0,
            "status": "MATCH",
        }
    ]
    assert receipt.matched_wme_indexes == {101}
    residual = match_wme_residual_movements(
        wme, excluded_indexes=receipt.matched_wme_indexes
    )
    assert {(r["operation_type"], r["document"]) for r in residual.residual_movements} == {
        ("PV", "1178"),
        ("F", "OTHER"),
    }


def test_rec004_quantity_difference_remains_in_wme_residual_review() -> None:
    wme = _wme(qty=11729.0)
    receipt = match_inbound_receipts(_wms(), wme)
    assert receipt.documents[0]["status"] == "QTY_DIFF"
    assert receipt.matched_wme_indexes == set()
    residual = match_wme_residual_movements(
        wme, excluded_indexes=receipt.matched_wme_indexes
    )
    assert ("F", "260769") in {
        (r["operation_type"], r["document"]) for r in residual.residual_movements
    }


def test_rec004_fe_priority_leaves_f_for_review() -> None:
    wme = _wme()
    wme.loc[104] = {
        "OperationType": "FE",
        "Document": "260769",
        "SignedQuantity": 11730.0,
        "Warehouse": "DEPOZIT PRINCIPAL",
    }
    receipt = match_inbound_receipts(_wms(), wme)
    assert receipt.documents[0]["wme_operation_type"] == "FE"
    assert receipt.matched_wme_indexes == {104}
    residual = match_wme_residual_movements(
        wme, excluded_indexes=receipt.matched_wme_indexes
    )
    assert ("F", "260769") in {
        (r["operation_type"], r["document"]) for r in residual.residual_movements
    }


def test_rec004_duplicate_wme_indexes_are_not_claimed() -> None:
    wme = _wme()
    wme.index = [101, 101, 103]
    receipt = match_inbound_receipts(_wms(), wme)
    assert receipt.documents[0]["status"] == "MATCH"
    assert receipt.matched_wme_indexes == set()

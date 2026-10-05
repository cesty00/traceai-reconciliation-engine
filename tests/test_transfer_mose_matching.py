from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.transfer_mose_matching import (
    match_transfer_mose,
    normalize_transfer_mose_order,
)


def _wme_nt(
    document: str,
    date: str,
    quantity: float,
    warehouse: str = "DEPOZIT PRINCIPAL",
    partner: str = "MOSE",
) -> dict:
    return {
        "Date": date,
        "OperationType": "NT",
        "Document": document,
        "SignedQuantity": quantity,
        "Warehouse": warehouse,
        "Partner": partner,
    }


def test_normalize_transfer_mose_order_strips_del_suffix() -> None:
    assert (
        normalize_transfer_mose_order(
            "TRANSFER_MOSE-202520828_DEL_D45092BA-D243"
        )
        == "TRANSFER_MOSE-202520828"
    )
    assert (
        normalize_transfer_mose_order("TRANSFER_MOSE-202520828")
        == "TRANSFER_MOSE-202520828"
    )


def test_transfer_mose_direct_document_match() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "23/04/2026 12:58:41",
                "Tip operatiune": "Receptie",
                "Cantitate": 100.0,
                "Numar comanda": "TRANSFER_MOSE-202520911",
                "Document intrare": 64857,
                "Document comanda": "NIR05336",
            }
        ]
    )
    wme = pd.DataFrame(
        [_wme_nt("64857", "23.04.2026", 100.0)]
    )

    result = match_transfer_mose(wms, wme)

    assert len(result.matches) == 1
    assert result.matches[0]["method"] == "DIRECT_DOCUMENT"
    assert result.matches[0]["wme_document"] == "64857"
    assert result.residual_wms_transfers == []


def test_transfer_mose_del_chain_nets_to_zero_without_nt() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "05/03/2026 08:28:11",
                "Tip operatiune": "Receptie",
                "Cantitate": 20.0,
                "Numar comanda": "TRANSFER_MOSE-202520828",
                "Document intrare": 62023,
                "Document comanda": "NEPROCESAT_5347",
            },
            {
                "Data": "05/03/2026 13:45:44",
                "Tip operatiune": "Receptie",
                "Cantitate": -20.0,
                "Numar comanda": (
                    "TRANSFER_MOSE-202520828_DEL_D45092BA-D243"
                ),
                "Document intrare": 62023,
                "Document comanda": "NEPROCESAT_5347",
            },
        ]
    )
    wme = pd.DataFrame(
        columns=[
            "Date",
            "OperationType",
            "Document",
            "SignedQuantity",
            "Warehouse",
            "Partner",
        ]
    )

    result = match_transfer_mose(wms, wme)

    assert result.matches == []
    assert len(result.cancelled_orders) == 1
    assert result.cancelled_orders[0]["status"] == "MATCH_DUPA_NETARE"
    assert result.residual_wms_transfers == []


def test_transfer_mose_unique_same_day_quantity_match() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "13/05/2026 10:00:00",
                "Tip operatiune": "Livrare",
                "Cantitate": -54.0,
                "Numar comanda": "TRANSFER_MOSE-202521000",
                "Document intrare": None,
                "Document comanda": "44117",
            }
        ]
    )
    wme = pd.DataFrame(
        [_wme_nt("67633", "13.05.2026", -54.0)]
    )

    result = match_transfer_mose(wms, wme)

    assert len(result.matches) == 1
    assert result.matches[0]["method"] == "SAME_DAY_QUANTITY"
    assert result.residual_wms_transfers == []


def test_transfer_mose_unique_short_lag_quantity_match() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "12/08/2026 10:00:00",
                "Tip operatiune": "Livrare",
                "Cantitate": -25.0,
                "Numar comanda": "TRANSFER_MOSE-202521162",
                "Document intrare": None,
                "Document comanda": "50861",
            }
        ]
    )
    wme = pd.DataFrame(
        [_wme_nt("75276", "13.08.2026", -25.0)]
    )

    result = match_transfer_mose(wms, wme)

    assert len(result.matches) == 1
    assert result.matches[0]["method"] == "LAG_QUANTITY"
    assert result.matches[0]["lag_days"] == 1


def test_transfer_mose_neprocesat_without_nt_remains_review() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "07/04/2026 13:01:10",
                "Tip operatiune": "Receptie",
                "Cantitate": 100.0,
                "Numar comanda": "TRANSFER_MOSE-202520904",
                "Document intrare": 64643,
                "Document comanda": "NEPROCESAT_5729",
            }
        ]
    )
    wme = pd.DataFrame(
        columns=[
            "Date",
            "OperationType",
            "Document",
            "SignedQuantity",
            "Warehouse",
            "Partner",
        ]
    )

    result = match_transfer_mose(wms, wme)

    assert len(result.residual_wms_transfers) == 1
    assert (
        result.residual_wms_transfers[0]["status"]
        == "NEPROCESAT_REVIEW"
    )


def test_transfer_mose_ambiguous_same_day_quantity_is_not_forced() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "24/06/2026 10:00:00",
                "Tip operatiune": "Livrare",
                "Cantitate": -3.0,
                "Numar comanda": "TRANSFER_MOSE-202521078",
                "Document intrare": None,
                "Document comanda": None,
            }
        ]
    )
    wme = pd.DataFrame(
        [
            _wme_nt("71341", "24.06.2026", -3.0),
            _wme_nt("71342", "24.06.2026", -3.0),
        ]
    )

    result = match_transfer_mose(wms, wme)

    assert result.matches == []
    assert len(result.residual_wms_transfers) == 1
    assert (
        result.residual_wms_transfers[0]["status"]
        == "NO_DOCUMENT_REVIEW"
    )

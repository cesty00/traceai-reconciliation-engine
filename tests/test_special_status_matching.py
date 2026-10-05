from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.special_status_matching import (
    match_special_status_flow,
)


def test_ins_det_deteriorate_candidate_matches_exact_chain() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "03/02/2026 09:21:40",
                "Tip operatiune": "Mutare intre gestiuni",
                "Cantitate": 546.0,
                "Locatie sursa": "INS.DPP",
                "Locatie destinatie": "INS.DET",
                "Cod-motiv": None,
                "Lot": "019.26",
            },
            {
                "Data": "03/02/2026 09:27:51",
                "Tip operatiune": "Mutare intre gestiuni",
                "Cantitate": 64.0,
                "Locatie sursa": "INS.DPP",
                "Locatie destinatie": "INS.DET",
                "Cod-motiv": None,
                "Lot": "022.26",
            },
            {
                "Data": "03/02/2026 09:35:59",
                "Tip operatiune": "Mutare intre gestiuni",
                "Cantitate": 8.0,
                "Locatie sursa": "ULMA",
                "Locatie destinatie": "INS.DET",
                "Cod-motiv": None,
                "Lot": "349.25",
            },
            {
                "Data": "04/03/2026 20:50:35",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -64.0,
                "Locatie sursa": "INS.DET",
                "Locatie destinatie": "INS.DET",
                "Cod-motiv": "COR STOC",
                "Lot": "022.26",
            },
            {
                "Data": "04/03/2026 20:55:09",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -546.0,
                "Locatie sursa": "INS.DET",
                "Locatie destinatie": "INS.DET",
                "Cod-motiv": "COR STOC",
                "Lot": "019.26",
            },
            {
                "Data": "04/03/2026 20:55:57",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -8.0,
                "Locatie sursa": "INS.DET",
                "Locatie destinatie": "INS.DET",
                "Cod-motiv": "COR STOC",
                "Lot": "349.25",
            },
        ]
    )

    wme = pd.DataFrame(
        [
            {
                "Date": "03.02.2026",
                "OperationType": "NT",
                "SignedQuantity": 64.0,
                "Warehouse": "DETERIORATE",
            },
            {
                "Date": "03.02.2026",
                "OperationType": "NT",
                "SignedQuantity": 8.0,
                "Warehouse": "DETERIORATE",
            },
            {
                "Date": "03.02.2026",
                "OperationType": "NT",
                "SignedQuantity": 538.0,
                "Warehouse": "DETERIORATE",
            },
            {
                "Date": "03.02.2026",
                "OperationType": "NT",
                "SignedQuantity": 8.0,
                "Warehouse": "DETERIORATE",
            },
        ]
    )

    result = match_special_status_flow(wms, wme)

    assert len(result.matched_groups) == 1
    match = result.matched_groups[0]
    assert match["wms_transfer_total"] == 618.0
    assert match["wme_nt_total"] == 618.0
    assert match["wms_correction_total"] == -618.0
    assert result.explained_total == -618.0
    assert result.residual_wms_corrections == []


def test_special_status_requires_wme_quantity_confirmation() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "03/02/2026 09:21:40",
                "Tip operatiune": "Mutare intre gestiuni",
                "Cantitate": 618.0,
                "Locatie sursa": "INS.DPP",
                "Locatie destinatie": "INS.DET",
                "Cod-motiv": None,
                "Lot": "019.26",
            },
            {
                "Data": "04/03/2026 20:55:09",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -618.0,
                "Locatie sursa": "INS.DET",
                "Locatie destinatie": "INS.DET",
                "Cod-motiv": "COR STOC",
                "Lot": "019.26",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "Date": "03.02.2026",
                "OperationType": "NT",
                "SignedQuantity": 600.0,
                "Warehouse": "DETERIORATE",
            }
        ]
    )

    result = match_special_status_flow(wms, wme)

    assert result.matched_groups == []
    assert result.explained_total == 0.0

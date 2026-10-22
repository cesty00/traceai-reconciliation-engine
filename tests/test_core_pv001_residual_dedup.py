from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.inventory_adjustment_matching import (
    match_inventory_adjustments,
)
from traceai_reconciliation.investigation.wme_residual_matching import (
    match_wme_residual_movements,
)


def test_pv001_unmatched_pv_retained_once_in_specialized_review() -> None:
    wms = pd.DataFrame(
        [
            {"Data": "2026-10-10", "Tip operatiune": "Ajustare negativa",
             "Cantitate": -86.35, "Cod-motiv": "INV-MIN"}
        ]
    )
    wme = pd.DataFrame(
        [
            {"Date": "2026-08-29", "OperationType": "PV", "Document": "1178",
             "SignedQuantity": 160.81, "Warehouse": "DEPOZIT PRINCIPAL"},
            {"Date": "2026-08-29", "OperationType": "F", "Document": "OTHER",
             "SignedQuantity": 7.0, "Warehouse": "DEPOZIT PRINCIPAL"},
        ],
        index=[70, 71],
    )
    inv = match_inventory_adjustments(wms, wme)
    assert inv.matches == []
    assert inv.residual_wme_pv[0]["document"] == "1178"
    assert inv.residual_wme_pv[0]["quantity"] == 160.81
    assert inv.reviewed_wme_pv_indexes == (70,)
    assert inv.system_difference_effect == -247.16

    generic = match_wme_residual_movements(
        wme,
        excluded_indexes=set(inv.matched_wme_indexes)
        | set(inv.reviewed_wme_pv_indexes),
    )
    assert [(v["operation_type"], v["document"]) for v in generic.residual_movements] == [
        ("F", "OTHER")
    ]


def test_pv001_matched_pv_is_not_reclassified_as_residual() -> None:
    wms = pd.DataFrame(
        [{"Data": "2026-08-28", "Tip operatiune": "Ajustare pozitiva",
          "Cantitate": 160.81, "Cod-motiv": "INV-PLS"}]
    )
    wme = pd.DataFrame(
        [{"Date": "2026-08-29", "OperationType": "PV", "Document": "1178",
          "SignedQuantity": 160.81, "Warehouse": "DEPOZIT PRINCIPAL"}],
        index=[72],
    )
    inv = match_inventory_adjustments(wms, wme)
    assert len(inv.matches) == 1
    assert inv.matched_wme_indexes == (72,)
    assert inv.reviewed_wme_pv_indexes == ()
    assert inv.residual_wme_pv == []


def test_pv001_missing_date_pv_remains_in_generic_review() -> None:
    wms = pd.DataFrame()
    wme = pd.DataFrame(
        [{"Date": None, "OperationType": "PV", "Document": "OTHER",
          "SignedQuantity": 5.0, "Warehouse": "DEPOZIT PRINCIPAL"}],
        index=[73],
    )
    inv = match_inventory_adjustments(wms, wme)
    assert inv.reviewed_wme_pv_indexes == ()
    generic = match_wme_residual_movements(
        wme, excluded_indexes=set(inv.reviewed_wme_pv_indexes)
    )
    assert len(generic.residual_movements) == 1

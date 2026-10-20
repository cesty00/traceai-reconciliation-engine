"""GOV-002N: real inventory-PV and WME-residual matcher ownership boundary.

Synthetic DataFrames carry stable row indices as source-row surrogates. These
are NOT file SHA/physical coordinates and NOT full-engine E2E acceptance.
"""
import pandas as pd

from traceai_reconciliation.investigation.inventory_adjustment_matching import (
    match_inventory_adjustments,
)
from traceai_reconciliation.investigation.wme_residual_matching import (
    match_wme_residual_movements,
)


def _sources(wme_quantity):
    wms = pd.DataFrame([{
        "Data": "2026-01-05",
        "Tip operatiune": "Ajustare negativa",
        "Cantitate": -10.0,
        "Cod-motiv": "INV-MIN",
    }], index=[41])
    wme = pd.DataFrame([{
        "Date": "2026-01-05",
        "OperationType": "PV",
        "SignedQuantity": wme_quantity,
        "Document": "PV-SYN-01",
        "Warehouse": "DEPOZIT PRINCIPAL",
    }], index=[17])
    return wms, wme


def test_gov_002n_confirmed_pv_line_excluded_from_wme_residual_review():
    wms, wme = _sources(-10.0)
    inventory = match_inventory_adjustments(wms, wme)
    assert len(inventory.matches) == 1
    assert inventory.matches[0]["status"] == "MATCH"
    assert inventory.matched_wme_indexes == (17,)
    assert inventory.system_difference_effect == 0.0

    residual = match_wme_residual_movements(
        wme, excluded_indexes=set(inventory.matched_wme_indexes)
    )
    assert residual.residual_movements == []
    assert residual.system_difference_effect == 0.0
    assert wme.loc[17, "SignedQuantity"] == -10.0


def test_gov_002n_unmatched_pv_line_remains_review_not_confirmed_delta():
    wms, wme = _sources(-9.0)
    inventory = match_inventory_adjustments(wms, wme)
    assert inventory.matches == []
    assert inventory.matched_wme_indexes == ()
    assert inventory.system_difference_effect == -1.0

    residual = match_wme_residual_movements(
        wme, excluded_indexes=set(inventory.matched_wme_indexes)
    )
    assert len(residual.residual_movements) == 1
    assert residual.residual_movements[0]["status"] == "WME_ONLY_REVIEW"
    assert residual.system_difference_effect == 9.0
    # Two matcher outputs must NOT be summed as independently confirmed effects:
    # residual is a REVIEW candidate, not an approved ledger event.

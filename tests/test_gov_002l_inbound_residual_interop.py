"""GOV-002L: source-row exclusion between real inbound and residual matchers.

Synthetic in-memory operational rows. This is a matcher integration test,
not proof of the complete investigate_product ownership invariant.
"""
import pandas as pd

from traceai_reconciliation.investigation.receipt_matching import match_inbound_receipts
from traceai_reconciliation.investigation.wme_residual_matching import (
    confirmed_inbound_wme_indexes,
    match_wme_residual_movements,
)


def _source_rows(wme_quantity: float):
    wms = pd.DataFrame([{
        "Tip operatiune": "Receptie",
        "Cantitate": 10.0,
        "Numar comanda": "IN100",
        "Document intrare": "F88",
    }], index=[41])
    wme = pd.DataFrame([{
        "OperationType": "FE",
        "Document": "F88",
        "SignedQuantity": wme_quantity,
        "Warehouse": "DEPOZIT PRINCIPAL",
    }], index=[17])
    return wms, wme


def test_gov_002l_exact_inbound_wme_row_not_reclassified_as_residual():
    wms, wme = _source_rows(10.0)
    receipts = match_inbound_receipts(wms, wme)
    assert len(receipts.documents) == 1
    assert receipts.documents[0]["status"] == "MATCH"
    excluded = confirmed_inbound_wme_indexes(wme, receipts.documents)
    assert excluded == {17}
    residual = match_wme_residual_movements(wme, excluded_indexes=excluded)
    assert residual.residual_movements == []
    assert residual.system_difference_effect == 0.0
    assert wme.loc[17, "SignedQuantity"] == 10.0


def test_gov_002l_quantity_mismatch_does_not_hide_wme_source_row():
    wms, wme = _source_rows(9.0)
    receipts = match_inbound_receipts(wms, wme)
    assert receipts.documents[0]["status"] == "QTY_DIFF"
    assert receipts.residual_total == 1.0
    excluded = confirmed_inbound_wme_indexes(wme, receipts.documents)
    assert excluded == set()
    residual = match_wme_residual_movements(wme, excluded_indexes=excluded)
    assert len(residual.residual_movements) == 1
    assert residual.residual_movements[0]["status"] == "WME_ONLY_REVIEW"
    assert residual.system_difference_effect == -9.0

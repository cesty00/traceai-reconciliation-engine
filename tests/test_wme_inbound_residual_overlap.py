import pandas as pd
from traceai_reconciliation.investigation.wme_residual_matching import (
    confirmed_inbound_wme_indexes, match_wme_residual_movements,
)

def test_matched_supplier_receipts_are_not_wme_residuals():
    rows=pd.DataFrame([
        {"OperationType":"FE","Document":"4610900","Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":5.0},
        {"OperationType":"FE","Document":"4611219","Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":5120.0},
        {"OperationType":"F","Document":"999","Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":7.0},
    ],index=[82563,82565,82599])
    matches=[
        {"document":"4610900","wme_operation_type":"FE","wme_quantity":5.0,"status":"MATCH"},
        {"document":"4611219","wme_operation_type":"FE","wme_quantity":5120.0,"status":"MATCH"},
    ]
    excluded=confirmed_inbound_wme_indexes(rows,matches)
    assert excluded=={82563,82565}
    residual=match_wme_residual_movements(rows,excluded_indexes=excluded)
    assert len(residual.residual_movements)==1
    assert residual.residual_movements[0]["document"]=="999"

def test_nonmatch_or_quantity_ambiguity_stays_review():
    rows=pd.DataFrame([
        {"OperationType":"FE","Document":"4611219","Warehouse":"DEP","SignedQuantity":5120.0},
    ],index=[17])
    for status,quantity in [("QTY_DIFF",5120.0),("MATCH",5119.0)]:
        excluded=confirmed_inbound_wme_indexes(rows,[{
            "document":"4611219","wme_operation_type":"FE",
            "wme_quantity":quantity,"status":status,
        }])
        assert excluded==set()
        assert match_wme_residual_movements(rows,excluded_indexes=excluded).residual_movements

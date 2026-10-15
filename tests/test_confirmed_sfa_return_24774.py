import pandas as pd
from traceai_reconciliation.investigation.delivery_matching import match_deliveries_and_returns


def test_confirmed_sfa_partial_return_is_netted_with_ae():
    wms = pd.DataFrame([
        {"Tip operatiune": "Livrare", "Numar comanda": "SFA24774", "Cantitate": -900},
        {"Tip operatiune": "Livrare", "Numar comanda": "SFA24774", "Cantitate": -900},
        {"Tip operatiune": "Livrare", "Numar comanda": "SFA24774", "Cantitate": -900},
        {"Tip operatiune": "Receptie", "Numar comanda": "SFA24774-1", "Cantitate": 300},
    ])
    wme = pd.DataFrame([{"OperationType": "AE", "Document": "24774", "SignedQuantity": -2400}])
    actual = match_deliveries_and_returns(wms, wme)
    assert actual.derived_receipt_documents == 1
    assert actual.residual_documents == []
    assert actual.documents[0]["document"] == "24774"
    assert actual.documents[0]["wms_net_quantity"] == -2400
    assert actual.documents[0]["wme_ae_quantity"] == -2400


def test_unrelated_sfa_receipt_not_automatically_consumed():
    wms = pd.DataFrame([
        {"Tip operatiune": "Livrare", "Numar comanda": "SFA24774", "Cantitate": -900},
        {"Tip operatiune": "Receptie", "Numar comanda": "SFA99999-1", "Cantitate": 300},
    ])
    wme = pd.DataFrame([{"OperationType": "AE", "Document": "24774", "SignedQuantity": -900}])
    result = match_deliveries_and_returns(wms, wme)
    assert next(x for x in result.documents if x["document"]=="24774")["wms_net_quantity"] == -900

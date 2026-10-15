import pandas as pd
from traceai_reconciliation.investigation.operation_timeline import timeline_from_wme

def test_wme_column_p_is_user():
    frame=pd.DataFrame([dict(Note="OPERATOR_WME_01",Date="2026-02-08",Document="2250",OperationType="PV",SignedQuantity=-9832.28,Warehouse="SECTIE PRODUCTIE",SourceRowNumber=67192,LineNo=66902)])
    item=timeline_from_wme(frame)[0]
    assert item["actor"] == {"user":"OPERATOR_WME_01"}
    assert item["source_row"] == 67192
    assert item["document"] == "2250"

def test_empty_wme_column_p_does_not_invent_user():
    frame=pd.DataFrame([dict(Note=None,Date="2026-02-08",Document="2250",OperationType="PV",SignedQuantity=-1)])
    assert "actor" not in timeline_from_wme(frame)[0]

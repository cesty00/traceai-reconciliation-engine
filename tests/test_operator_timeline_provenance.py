import pandas as pd
from traceai_reconciliation.investigation.operation_timeline import timeline_from_wms, timeline_from_wme
from traceai_reconciliation.reports.operator_causes_report import _source_reference

def test_indexed_wms_return_source_row_reaches_docx():
    frame = pd.DataFrame([{
        "Data": "2026-10-02 14:29:24",
        "Numar comanda": "SFA24774-1",
        "Tip operatiune": "Receptie",
        "Cantitate": 300.0,
        "Gestiune": "Depozit Principal",
        "SourceRowNumber": 75956,
    }])
    entry = timeline_from_wms(frame)[0]
    assert entry["document"] == "SFA24774-1"
    assert entry["source_row"] == 75956
    assert _source_reference(entry) == "75956"

def test_no_invented_row_on_nonindexed_source():
    frame = pd.DataFrame([{
        "Data": "2026-10-02",
        "Numar comanda": "SFA24774-1",
        "Tip operatiune": "Receptie",
        "Cantitate": 300.0,
        "Gestiune": "Depozit Principal",
    }])
    entry = timeline_from_wms(frame)[0]
    assert entry["source_row"] is None
    assert _source_reference(entry) == "Nedisponibil în cronologia cazului"

def test_wme_source_row_and_line_no_distinct():
    frame = pd.DataFrame([{
        "Date": "2026-05-06", "Document": "92766", "OperationType": "F",
        "SignedQuantity": -20.0, "Warehouse": "MOSE", "Partner": "MONTELUX",
        "SourceRowNumber": 125001, "LineNo": 86,
    }])
    entry = timeline_from_wme(frame)[0]
    assert entry["source_row"] == 125001
    assert entry["source_line_no"] == 86

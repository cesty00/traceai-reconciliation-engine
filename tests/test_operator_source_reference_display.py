from pathlib import Path
from docx import Document
from traceai_reconciliation.reports.operator_causes_report import _date_for_operator, _source_reference
def test_operator_date_and_source_reference_are_conservative():
    assert _date_for_operator("2026-05-06 00:00:00") == "06.05.2026"
    assert _date_for_operator("2026-10-02 14:29:24") == "02.10.2026 14:29:24"
    assert _date_for_operator("-") == "Neidentificată"
    assert _source_reference({"document":"SFA24774"}) == "Nedisponibil în cronologia cazului"
    assert _source_reference({"source_row":75956}) == "75956"

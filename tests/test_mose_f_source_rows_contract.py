from __future__ import annotations

from pathlib import Path

from docx import Document
from traceai_reconciliation.reports.operator_causes_report import _date_for_operator


def test_mose_invoice_rows_are_source_derived_not_summary_effect():
    source = (Path(__file__).resolve().parents[1] / "src/traceai_reconciliation/reports/operator_causes_report.py").read_text(encoding="utf-8")
    assert 'if system == "WME" and operation == "F"' in source
    assert 'sum(float(e.get("quantity") or 0) for e in matches)' in source
    assert '", ".join(dict.fromkeys(_source_reference(e) for e in matches))' in source
    assert 'nu există gestiune MOSE și nici sold MOSE în WMS' in source
    assert _date_for_operator("2026-08-12 00:00:00") == "12.08.2026"

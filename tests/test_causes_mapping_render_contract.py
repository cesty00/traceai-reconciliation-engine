import ast
from pathlib import Path

def test_operator_causes_includes_mapping_explanation_and_source_documents():
    source=(Path(__file__).resolve().parents[1] / "src/traceai_reconciliation/reports/operator_causes_report.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert 'Maparea diferenței raportate pe gestiuni' in source
    assert 'WME fișă magazie' in source
    assert 'Operațiuni WME în gestiunea afectată' in source
    assert 'dublei clasificări' in source or 'duble clasificări' in source

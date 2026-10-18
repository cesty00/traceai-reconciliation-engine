import ast
from pathlib import Path


def test_report_mapping_full_vs_partial_has_distinct_causes():
    source = (Path(__file__).resolve().parents[1] /
              "src/traceai_reconciliation/investigation/engine.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert 'mapping_explains_full_report_difference' in source
    assert 'not stock_zone_match.unresolved_rows' in source
    assert 'abs(mapping_effect - result.initial_difference)' in source
    assert 'CAUSE-REPORT-MAPPING-FULL' in source
    assert 'CAUSE-REPORT-MAPPING-PARTIAL' in source
    assert 'result.verdict = "REVIEW"' in source

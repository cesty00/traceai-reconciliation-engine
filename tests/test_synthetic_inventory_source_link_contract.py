from __future__ import annotations

from pathlib import Path


def test_synthetic_inventory_findings_link_only_unique_original_wms_adjustment():
    source = (Path(__file__).resolve().parents[1] / "src/traceai_reconciliation/reports/operator_causes_report.py").read_text(encoding="utf-8")
    assert 'if system == "WMS" and operation in ("INV-MIN", "INV-PLS")' in source
    assert 'if len(candidates) == 1:' in source
    assert 'str(e.get("date") or "")[:10] != str(item.get("date") or "")[:10]' in source
    assert '_source_reference(e), str(item.get("reason") or "-")' in source

"""Headless Streamlit AppTest acceptance smoke using synthetic sensitive-free files.

Run through the dedicated Streamlit UI CI job with optional UI dependencies.
"""
import json
import sys
from pathlib import Path

import pytest
pytest.importorskip('streamlit', reason='UI dependency tested separately')
from streamlit.testing.v1 import AppTest


def test_daily_streamlit_readonly_renders_documents(tmp_path, monkeypatch):
    operator = {
        "schema_version": "1", "case_id": "SYN-UI-11",
        "product_code": "SYN-P", "product_name": "Synthetic item",
        "unit": "kg", "difference": -86.35, "cause": "Inventory residual",
        "cause_status": "REVIEW", "evidence_level": "B",
        "rules": ["INV-01"], "correction_target": "REVIEW",
        "operator_action": "Check original documents",
        "operator_status": "REVIEW", "residual": 0.0,
        "evidence": ["SYN-INV-01: grouped evidence"], "blockers": [],
        "warnings": ["Synthetic warning"],
        "wms_mutation_allowed": False, "wme_mutation_allowed": False,
    }
    case = {"investigation": {"case_id": "SYN-UI-11", "details": {
        "inventory_adjustment_matching": {"residual_wms_adjustments": [
            {"contributing_event_refs": [
                {"document": "00060", "lot": "SYN-LOT-A", "quantity": -131.75},
                {"document": "00060", "lot": "SYN-LOT-B", "quantity": -0.25},
                {"document": "00060", "lot": "SYN-LOT-C", "quantity": 45.65},
            ]},
        ]}
    }}}
    op_path = tmp_path / "operator.json"
    case_path = tmp_path / "case.json"
    op_path.write_text(json.dumps(operator), encoding="utf-8")
    case_path.write_text(json.dumps(case), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["daily_readonly.py", "--case", str(op_path),
                                      "--investigation", str(case_path)])
    app_path = Path(__file__).parents[1] / "apps" / "daily_readonly.py"
    at = AppTest.from_file(str(app_path), default_timeout=15).run()
    assert not at.exception
    assert any("DS" not in item.value and "SYN-P" in item.value for item in at.subheader)
    assert any("00060" in item.value for item in at.markdown)
    assert any("UNVERIFIED" in item.value for item in at.markdown)
    assert any("Validarea documentară" in item.value for item in at.warning)
    assert not at.button

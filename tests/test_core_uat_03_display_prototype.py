"""Synthetic, isolated acceptance tests for read-only presentation only."""
import copy
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).parents[1] / "prototypes/core_uat_03/operator_display.py"
spec = importlib.util.spec_from_file_location("uat03_display", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def automatic():
    return {
        "case_id": "SYN-01", "product_code": "SYN-PRODUCT",
        "difference": -10.0, "residual": 0.0,
        "operator_status": "CONFIRMAT",
        "evidence": [{"source_hash": "sha256-synthetic",
                      "document_ref": "SYN-DOC-1", "physical_row": 7}],
        "wms_mutation_allowed": False, "wme_mutation_allowed": False,
    }


def test_identification_does_not_mean_operator_validation(automatic):
    original = copy.deepcopy(automatic)
    view = module.build_operator_display(automatic)
    assert view["attribution_status"] == "CAUSE_IDENTIFIED"
    assert view["justification_status"] == "OPERATIONAL_REVIEW"
    assert view["economic_verdict_unchanged"] == "CONFIRMAT"
    assert not view["automatic_approval_allowed"]
    assert automatic == original


def test_explicit_documented_validation_only_changes_rationale(automatic):
    validated = module.build_operator_display(automatic, {
        "reason_code": "INVENTORY", "comment": "Physical count documented",
        "supporting_document": "SYN-PV", "reviewer": "SYN-REVIEWER",
        "validated_at": "2026-10-20T12:00:00Z", "scope": "SYN-DOC-1",
    })
    assert validated["justification_status"] == "OPERATOR_VALIDATED"
    assert validated["difference"] == -10.0
    assert validated["residual"] == 0.0
    assert not validated["wme_mutation_allowed"]


def test_unknown_reason_remains_review(automatic):
    result = module.build_operator_display(automatic, {"reason_code": "UNKNOWN"})
    assert result["justification_status"] == "OPERATIONAL_REVIEW"


def test_missing_source_row_fails_attribution_closed(automatic):
    automatic["evidence"][0].pop("physical_row")
    result = module.build_operator_display(automatic)
    assert result["attribution_status"] == "REVIEW"


def test_missing_supporting_document_not_validated(automatic):
    result = module.build_operator_display(automatic, {
        "reason_code": "INVENTORY", "comment": "Counted",
        "reviewer": "SYN-REVIEWER", "validated_at": "2026-10-20T12:00:00Z",
        "scope": "SYN-DOC-1",
    })
    assert result["justification_status"] == "OPERATIONAL_REVIEW"


def test_mutation_authority_rejected(automatic):
    automatic["wme_mutation_allowed"] = True
    with pytest.raises(ValueError):
        module.build_operator_display(automatic)


def test_invalid_reason_rejected(automatic):
    with pytest.raises(ValueError):
        module.build_operator_display(automatic, {"reason_code": "MATCH"})

"""CORE-UAT-04C: pending acceptance requirements, isolated from CORE production.

The test is an explicit expected failure until INV-01 explains its contributing
document and immutable source pointers. A green suite is NOT acceptance.
"""
from __future__ import annotations

import pytest

from traceai_reconciliation.investigation.auto_explain import (
    components_from_investigation,
)
from traceai_reconciliation.investigation.models import ProductInvestigationResult


def synthetic_case():
    result = ProductInvestigationResult(
        case_id="SYN-UAT-04C", product_code="SYN-PRODUCT",
        product_name="Synthetic inventory item", unit="KG",
        period="2026-10-01/2026-10-11", report_date="2026-10-11",
        initial_difference=-10.0, unexplained_difference=0.0,
        explained_difference=-10.0,
    )
    result.details["inventory_adjustment_matching"] = {
        "applied_to_explanation": True,
        "system_difference_effect": -10.0,
        "contributing_documents": [{
            "document": "SYN-INV-001",
            "events": [
                {"source": "WMS", "physical_row": 5, "qty": -12.0,
                 "sha256": "a" * 64},
                {"source": "WMS", "physical_row": 6, "qty": 2.0,
                 "sha256": "a" * 64},
            ],
        }],
    }
    return result


@pytest.mark.xfail(
    strict=True,
    reason="CORE-UAT-04C OPEN: INV-01 explanation component lacks explicit document + source-row links",
)
def test_inv01_component_identifies_contributing_document_and_rows():
    result = synthetic_case()
    components = components_from_investigation(result)
    inv = [c for c in components if c.rule_id == "INV-01" and c.contributes]
    assert len(inv) == 1
    component = inv[0]
    assert component.effect == -10.0
    # Desired evidence bridge contract: explicit rather than inferred from the timeline.
    assert "SYN-INV-001" in component.description
    assert "5" in component.description and "6" in component.description


def test_inv01_never_changes_report_difference():
    result = synthetic_case()
    original = (result.initial_difference, result.explained_difference,
                result.unexplained_difference, result.verdict)
    components_from_investigation(result)
    assert (result.initial_difference, result.explained_difference,
            result.unexplained_difference, result.verdict) == original

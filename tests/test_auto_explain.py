from __future__ import annotations

import pytest

from traceai_reconciliation.investigation.auto_explain import (
    ExplanationComponent,
    auto_explanation_from_investigation,
    components_from_investigation,
    compose_explanation,
    opening_component,
)
from traceai_reconciliation.investigation.models import ProductInvestigationResult


def component(
    component_id: str,
    rule_id: str,
    effect: float,
    *,
    evidence: str = "A",
    status: str = "CONFIRMED",
    contributes: bool = True,
) -> ExplanationComponent:
    return ExplanationComponent(
        component_id=component_id,
        rule_id=rule_id,
        effect=effect,
        description=component_id,
        evidence_level=evidence,
        status=status,
        contributes=contributes,
    )


def test_exact_multi_component_equation_from_golden_pattern() -> None:
    result = compose_explanation(
        -70.0,
        [
            component("opening", "OPEN-01", -1.0),
            component("production", "PROD-02", -202.0),
            component("wme_pv", "GST-04", 140.0),
            component("delivery", "DEL-02", -7.0),
        ],
    )

    assert result.status == "EXACT"
    assert result.explained_difference == -70.0
    assert result.residual_difference == 0.0
    assert result.evidence_level == "A"
    assert result.rules == ("OPEN-01", "PROD-02", "GST-04", "DEL-02")
    assert "rezidual 0.000" in result.equation


def test_opening_only_case_is_exact() -> None:
    opening = opening_component(72.0, 76.0)
    assert opening is not None

    result = compose_explanation(-4.0, [opening])

    assert result.status == "EXACT"
    assert result.rules == ("OPEN-01",)
    assert result.residual_difference == 0.0


def test_probable_component_is_not_used_by_default() -> None:
    result = compose_explanation(
        -25.0,
        [
            component("opening", "OPEN-01", -1.0),
            component(
                "candidate_adjustment",
                "ADJ-01",
                -24.0,
                evidence="B",
                status="PROBABLE",
            ),
        ],
    )

    assert result.status == "PARTIAL"
    assert result.explained_difference == -1.0
    assert result.residual_difference == -24.0
    assert result.rules == ("OPEN-01",)


def test_probable_component_can_be_enabled_explicitly() -> None:
    result = compose_explanation(
        -25.0,
        [
            component("opening", "OPEN-01", -1.0),
            component(
                "candidate_adjustment",
                "ADJ-01",
                -24.0,
                evidence="B",
                status="PROBABLE",
            ),
        ],
        include_probable=True,
    )

    assert result.status == "EXACT"
    assert result.evidence_level == "B"
    assert result.residual_difference == 0.0


def test_non_contributing_and_review_components_do_not_change_math() -> None:
    result = compose_explanation(
        -17.0,
        [
            component("opening", "OPEN-01", -17.32),
            component("pv", "GST-04", 16.32),
            component("production", "PROD-02", -16.0),
            component(
                "timing_only",
                "TIMING",
                7.0,
                status="REVIEW",
            ),
            component(
                "matched_transfer",
                "TRANSFER",
                999.0,
                contributes=False,
            ),
        ],
    )

    assert result.status == "EXACT"
    assert result.explained_difference == -17.0
    assert result.residual_difference == 0.0


def test_duplicate_component_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="apare de mai multe ori"):
        compose_explanation(
            -10.0,
            [
                component("same", "OPEN-01", -5.0),
                component("same", "ADJ-01", -5.0),
            ],
        )


def test_wrong_direction_components_are_inconsistent() -> None:
    result = compose_explanation(
        -10.0,
        [component("wrong", "ADJ-01", 5.0)],
    )

    assert result.status == "INCONSISTENT"
    assert result.residual_difference == -15.0



def investigation_result(
    *,
    initial_difference: float,
    opening_wms: float | None = None,
    opening_wme: float | None = None,
    details: dict | None = None,
) -> ProductInvestigationResult:
    return ProductInvestigationResult(
        case_id="CASE-TEST-AUTO",
        product_code="TEST001",
        product_name="Produs test",
        unit="KG",
        period="01.01.2026-04.10.2026",
        report_date="07.10.2026",
        initial_difference=initial_difference,
        opening_stock_wms=opening_wms,
        opening_stock_wme=opening_wme,
        details=details or {},
    )


def test_adapter_uses_only_applied_components() -> None:
    result = investigation_result(
        initial_difference=-70.0,
        opening_wms=76.0,
        opening_wme=77.0,
        details={
            "production_matching": {
                "residual_total": -202.0,
                "applied_to_explanation": True,
            },
            "delivery_matching": {
                "residual_total": -7.0,
                "applied_to_explanation": True,
            },
            "special_status_matching": {
                "explained_total": 140.0,
                "applied_to_explanation": True,
            },
            "generic_stock_corrections": {
                "residual_total": -999.0,
                "applied_to_explanation": False,
            },
        },
    )

    explanation = auto_explanation_from_investigation(result)

    assert explanation.status == "EXACT"
    assert explanation.explained_difference == -70.0
    assert explanation.residual_difference == 0.0
    assert explanation.rules == (
        "OPEN-01",
        "PROD-02",
        "DEL-02",
        "GST-04",
    )


def test_adapter_ignores_unapplied_details() -> None:
    result = investigation_result(
        initial_difference=-10.0,
        details={
            "production_matching": {
                "residual_total": -10.0,
                "applied_to_explanation": False,
            },
            "delivery_matching": {
                "residual_total": -10.0,
                "applied_to_explanation": False,
            },
        },
    )

    components = components_from_investigation(result)
    explanation = auto_explanation_from_investigation(result)

    assert components == []
    assert explanation.status == "NONE"
    assert explanation.explained_difference == 0.0
    assert explanation.residual_difference == -10.0


def test_adapter_extracts_opening_only() -> None:
    result = investigation_result(
        initial_difference=-4.0,
        opening_wms=72.0,
        opening_wme=76.0,
    )

    components = components_from_investigation(result)
    explanation = auto_explanation_from_investigation(result)

    assert len(components) == 1
    assert components[0].rule_id == "OPEN-01"
    assert explanation.status == "EXACT"
    assert explanation.residual_difference == 0.0

from __future__ import annotations

from traceai_reconciliation.investigation.auto_explain import (
    auto_explanation_from_investigation,
)
from traceai_reconciliation.investigation.models import ProductInvestigationResult
from traceai_reconciliation.investigation.promotion_gate import (
    assess_auto_explain_promotion,
)


def result(*, diff: float, details: dict | None = None) -> ProductInvestigationResult:
    return ProductInvestigationResult(
        case_id="CASE-PROMOTION",
        product_code="TEST",
        product_name="Test",
        unit="KG",
        period="01.01.2026-04.10.2026",
        report_date="07.10.2026",
        initial_difference=diff,
        details=details or {},
    )


def test_partial_explanation_is_held() -> None:
    investigation = result(diff=-10.0)
    explanation = auto_explanation_from_investigation(investigation)

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert assessment.status == "HOLD"
    assert "AUTO_EXPLAIN_NOT_EXACT" in assessment.blockers


def test_exact_opening_a_level_can_enter_human_review() -> None:
    investigation = result(diff=-1.0)
    investigation.opening_stock_wms = 0.0
    investigation.opening_stock_wme = 1.0
    explanation = auto_explanation_from_investigation(investigation)

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert explanation.status == "EXACT"
    assert assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW"
    assert assessment.eligible_for_review is True
    assert assessment.blockers == ()


def test_exact_b_evidence_stays_hold() -> None:
    investigation = result(
        diff=-10.0,
        details={
            "delivery_matching": {
                "residual_total": -10.0,
                "applied_to_explanation": True,
            }
        },
    )
    explanation = auto_explanation_from_investigation(investigation)

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert explanation.status == "EXACT"
    assert assessment.status == "HOLD"
    assert any(
        blocker.startswith("EVIDENCE_LEVEL_B")
        for blocker in assessment.blockers
    )


def test_wme02_exact_is_blocked_by_competing_unresolved_families() -> None:
    investigation = result(
        diff=1.0,
        details={
            "wme_residual_movements": {
                "movements": [
                    {
                        "operation_type": "PV",
                        "document": "2482",
                        "system_difference_effect": 1.0,
                    }
                ]
            },
            "production_matching": {
                "document_residual_total": 126.0,
                "document_residuals": [
                    {"effective_difference": 126.0}
                ],
                "applied_to_explanation": False,
            },
            "delivery_matching": {
                "residual_total": -10400.0,
                "applied_to_explanation": False,
            },
            "generic_stock_corrections": {
                "residual_total": -9.0,
                "applied_to_explanation": False,
            },
        },
    )
    explanation = auto_explanation_from_investigation(investigation)

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert explanation.status == "EXACT"
    assert explanation.rules == ("WME-02",)
    assert assessment.status == "HOLD"
    assert "UNRESOLVED_PRODUCTION_DOCUMENT_RESIDUAL" in assessment.blockers
    assert "UNRESOLVED_DELIVERY_RESIDUAL" in assessment.blockers
    assert "UNRESOLVED_GENERIC_STOCK_CORRECTION" in assessment.blockers


def test_prod03_exact_is_blocked_if_large_generic_correction_is_unowned() -> None:
    investigation = result(
        diff=-428.4,
        details={
            "production_input_matching": {
                "persistent_residual_total": -428.4,
                "safe_to_auto_explain": True,
                "applied_to_explanation": False,
            },
            "generic_stock_corrections": {
                "residual_total": -1127.6,
                "applied_to_explanation": False,
            },
        },
    )
    explanation = auto_explanation_from_investigation(investigation)

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert explanation.status == "EXACT"
    assert explanation.rules == ("PROD-03",)
    assert assessment.status == "HOLD"
    assert "UNRESOLVED_GENERIC_STOCK_CORRECTION" in assessment.blockers


def test_tolerance_only_exact_is_classified_separately() -> None:
    investigation = result(diff=0.001)
    explanation = auto_explanation_from_investigation(investigation)

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert explanation.status == "EXACT"
    assert explanation.components == ()
    assert assessment.status == "TOLERANCE_MATCH"
    assert assessment.eligible_for_review is True

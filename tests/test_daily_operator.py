from __future__ import annotations

from traceai_reconciliation.investigation.auto_explain import (
    AutoExplanation,
    ExplanationComponent,
)
from traceai_reconciliation.investigation.daily_operator import (
    build_daily_operator_result,
)
from traceai_reconciliation.investigation.models import ProductInvestigationResult
from traceai_reconciliation.investigation.promotion_gate import PromotionAssessment


def _investigation() -> ProductInvestigationResult:
    return ProductInvestigationResult(
        case_id="CASE-1",
        product_code="DS001",
        product_name="Produs test",
        unit="KG",
        period="01.01.2026-11.10.2026",
        report_date="11.10.2026",
        initial_difference=5.0,
        cause_description="Diferenta de mapare gestiune speciala.",
        cause_status="DETERMINATA",
    )


def test_operator_view_for_gst_mapping_forbids_stock_mutation() -> None:
    result = _investigation()
    explanation = AutoExplanation(
        initial_difference=5.0,
        explained_difference=5.0,
        residual_difference=0.0,
        status="EXACT",
        evidence_level="A",
        rules=("GST-02", "GST-03"),
        equation="5.000 = 5.000",
        components=(
            ExplanationComponent(
                component_id="gst-mostre",
                rule_id="GST-02",
                effect=5.0,
                description="MOSTRE exista in ambele sisteme, dar nu intra in ERP.",
                evidence_level="A",
                source="stock_report+wme_ledger",
            ),
        ),
    )
    assessment = PromotionAssessment(
        status="ELIGIBLE_FOR_HUMAN_REVIEW",
        eligible_for_review=True,
        blockers=(),
        warnings=(),
        explanation_status="EXACT",
        evidence_level="A",
        rules=("GST-02", "GST-03"),
    )

    view = build_daily_operator_result(result, explanation, assessment)

    assert view.operator_status == "CONFIRMAT"
    assert view.correction_target == "REPORT_MAPPING"
    assert view.residual == 0.0
    assert view.wms_mutation_allowed is False
    assert view.wme_mutation_allowed is False
    assert "Nu modifica stocul WMS/WME" in view.operator_action


def test_operator_view_for_opening_mismatch_points_to_opening_balance() -> None:
    result = _investigation()
    result.initial_difference = -1.0
    explanation = AutoExplanation(
        initial_difference=-1.0,
        explained_difference=-1.0,
        residual_difference=0.0,
        status="EXACT",
        evidence_level="A",
        rules=("OPEN-01",),
        equation="-1.000 = -1.000",
        components=(
            ExplanationComponent(
                component_id="opening",
                rule_id="OPEN-01",
                effect=-1.0,
                description="Opening WMS 0 versus WME 1.",
                evidence_level="A",
                source="opening_stock",
            ),
        ),
    )
    assessment = PromotionAssessment(
        status="ELIGIBLE_FOR_HUMAN_REVIEW",
        eligible_for_review=True,
        blockers=(),
        warnings=(),
        explanation_status="EXACT",
        evidence_level="A",
        rules=("OPEN-01",),
    )

    view = build_daily_operator_result(result, explanation, assessment)

    assert view.correction_target == "OPENING_BALANCE"
    assert view.operator_status == "CONFIRMAT"
    assert "soldul initial WMS versus WME" in view.operator_action


def test_operator_view_stays_review_on_hold() -> None:
    result = _investigation()
    explanation = AutoExplanation(
        initial_difference=5.0,
        explained_difference=0.0,
        residual_difference=5.0,
        status="PARTIAL",
        evidence_level="B",
        rules=(),
        equation="0 = 5.000 (rezidual 5.000)",
        components=(),
    )
    assessment = PromotionAssessment(
        status="HOLD",
        eligible_for_review=False,
        blockers=("INSUFFICIENT_DIRECT_EVIDENCE",),
        warnings=(),
        explanation_status="PARTIAL",
        evidence_level="B",
        rules=(),
    )

    view = build_daily_operator_result(result, explanation, assessment)

    assert view.operator_status == "REVIEW"
    assert view.correction_target == "REVIEW"
    assert view.residual == 5.0
    assert "Nu corecta stocul inca" in view.operator_action

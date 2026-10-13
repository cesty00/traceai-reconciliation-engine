from __future__ import annotations

from dataclasses import asdict

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

    # A BC residual without verified stock effect is NOT an exact explanation.
    assert explanation.status == "NONE"
    assert explanation.rules == ()
    assert assessment.status == "HOLD"
    assert "AUTO_EXPLAIN_NOT_EXACT" in assessment.blockers


def test_tolerance_only_exact_is_classified_separately() -> None:
    investigation = result(diff=0.001)
    explanation = auto_explanation_from_investigation(investigation)

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert explanation.status == "EXACT"
    assert explanation.components == ()
    assert assessment.status == "TOLERANCE_MATCH"
    assert assessment.eligible_for_review is True



def test_promotion_gate_is_read_only_on_investigation() -> None:
    investigation = result(
        diff=-1.0,
        details={
            "wme_residual_movements": {
                "movements": [
                    {
                        "operation_type": "PV",
                        "document": "TEST",
                        "system_difference_effect": -1.0,
                    }
                ]
            }
        },
    )
    before = asdict(investigation)
    explanation = auto_explanation_from_investigation(investigation)

    _ = assess_auto_explain_promotion(investigation, explanation)

    after = asdict(investigation)
    assert after == before



def test_prod03_exact_ignores_generic_corrections_absorbed_by_checkpoint_and_neutralizer() -> None:
    investigation = result(
        diff=-439.6,
        details={
            "production_input_matching": {
                "persistent_residual_total": -439.6,
                "safe_to_auto_explain": True,
                "inventory_checkpoint_date": "2026-06-07 14:24:56",
                "neutralized_residual_documents": [
                    {
                        "document": "38457",
                        "neutralizing_correction": {
                            "date": "2026-09-14 07:42:44",
                            "quantity": -591.6,
                        },
                    }
                ],
                "applied_to_explanation": False,
            },
            "generic_stock_corrections": {
                "residual_total": -79357.35,
                "applied_to_explanation": False,
            },
        },
    )
    investigation.unmatched_operations = [
        {
            "date": "08/02/2026 16:17:30",
            "system": "WMS",
            "operation_type": "COR STOC",
            "quantity": -23891.10,
            "status": "WMS_ONLY_REVIEW",
        },
        {
            "date": "08/02/2026 16:18:05",
            "system": "WMS",
            "operation_type": "COR STOC",
            "quantity": -28839.45,
            "status": "WMS_ONLY_REVIEW",
        },
        {
            "date": "10/03/2026 12:06:11",
            "system": "WMS",
            "operation_type": "COR STOC",
            "quantity": -21000.0,
            "status": "WMS_ONLY_REVIEW",
        },
        {
            "date": "07/06/2026 14:24:56",
            "system": "WMS",
            "operation_type": "COR STOC",
            "quantity": -5035.2,
            "status": "WMS_ONLY_REVIEW",
        },
        {
            "date": "14/09/2026 07:42:44",
            "system": "WMS",
            "operation_type": "COR STOC",
            "quantity": -591.6,
            "status": "WMS_ONLY_REVIEW",
        },
    ]
    explanation = auto_explanation_from_investigation(investigation)

    assessment = assess_auto_explain_promotion(investigation, explanation)

    # A checkpoint plus a linked correction does not by itself prove the
    # contribution of the BC residual to the final stock difference.
    assert explanation.status == "NONE"
    assert explanation.rules == ()
    assert assessment.status == "HOLD"
    assert "AUTO_EXPLAIN_NOT_EXACT" in assessment.blockers


def test_exact_stock_report_mapping_is_reviewable_when_system_movements_balance() -> None:
    investigation = result(
        diff=6.0,
        details={
            "wms_net_movement": 16364.5,
            "wme_net_movement": 16364.5,
            "stock_report_zone_matching": {
                "mapping_effect_total": 6.0,
                "unresolved_rows": 1,
                "applied_to_explanation": True,
            },
            "generic_stock_corrections": {
                "residual_total": -229.5,
                "applied_to_explanation": False,
            },
        },
    )
    from traceai_reconciliation.investigation.auto_explain import (
        AutoExplanation,
        ExplanationComponent,
    )
    explanation = AutoExplanation(
        initial_difference=6.0,
        explained_difference=6.0,
        residual_difference=0.0,
        status="EXACT",
        evidence_level="A",
        rules=("GST-02/GST-03",),
        components=(
            ExplanationComponent(
                component_id="stock_report_zone_mapping",
                rule_id="GST-02/GST-03",
                effect=6.0,
                description="mapping",
                evidence_level="A",
                source="stock_report_zone_matching",
                status="CONFIRMED",
            ),
        ),
        equation="6 = 6",
    )

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW"
    assert "UNRESOLVED_GENERIC_STOCK_CORRECTION" not in assessment.blockers
    assert "UNRESOLVED_STOCK_REPORT_ZONE_MAPPING" not in assessment.blockers


def test_stock_report_mapping_remains_hold_when_system_movements_do_not_balance() -> None:
    investigation = result(
        diff=6.0,
        details={
            "wms_net_movement": 16364.5,
            "wme_net_movement": 16358.5,
            "stock_report_zone_matching": {
                "mapping_effect_total": 6.0,
                "unresolved_rows": 1,
                "applied_to_explanation": True,
            },
            "generic_stock_corrections": {
                "residual_total": -229.5,
                "applied_to_explanation": False,
            },
        },
    )
    from traceai_reconciliation.investigation.auto_explain import (
        AutoExplanation,
        ExplanationComponent,
    )
    explanation = AutoExplanation(
        initial_difference=6.0,
        explained_difference=6.0,
        residual_difference=0.0,
        status="EXACT",
        evidence_level="A",
        rules=("GST-02/GST-03",),
        components=(
            ExplanationComponent(
                component_id="stock_report_zone_mapping",
                rule_id="GST-02/GST-03",
                effect=6.0,
                description="mapping",
                evidence_level="A",
                source="stock_report_zone_matching",
                status="CONFIRMED",
            ),
        ),
        equation="6 = 6",
    )

    assessment = assess_auto_explain_promotion(investigation, explanation)

    assert assessment.status == "HOLD"
    assert "UNRESOLVED_GENERIC_STOCK_CORRECTION" in assessment.blockers
    assert "UNRESOLVED_STOCK_REPORT_ZONE_MAPPING" in assessment.blockers

from __future__ import annotations

from dataclasses import asdict

from traceai_reconciliation.investigation.auto_explain import (
    auto_explanation_from_investigation,
)
from traceai_reconciliation.investigation.human_review_queue import (
    apply_human_review_decision,
    build_human_review_queue_item,
    build_review_queue_payload,
    review_queue_values,
    record_manual_evidence_resolution,
)
from traceai_reconciliation.investigation.models import ProductInvestigationResult
from traceai_reconciliation.investigation.promotion_gate import (
    assess_auto_explain_promotion,
)


def result(*, diff: float, details: dict | None = None) -> ProductInvestigationResult:
    return ProductInvestigationResult(
        case_id="CASE-V07",
        product_code="TEST-V07",
        product_name="Test v0.7",
        unit="KG",
        period="01.01.2026-04.10.2026",
        report_date="07.10.2026",
        initial_difference=diff,
        details=details or {},
    )


def test_eligible_case_is_staged_not_approved() -> None:
    investigation = result(diff=-1.0)
    investigation.opening_stock_wms = 0.0
    investigation.opening_stock_wme = 1.0
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)

    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        evidence_url="https://example.invalid/evidence",
        execution_id="RUN-V07",
        staged_at="2026-10-07T18:00:00+00:00",
    )

    assert assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW"
    assert item.review_status == "STAGED"
    assert item.human_decision is None
    assert item.registry_action == "NONE"
    assert item.priority == "P1"


def test_hold_case_keeps_blockers_and_cannot_imply_approval() -> None:
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

    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    assert assessment.status == "HOLD"
    assert item.promotion_status == "HOLD"
    assert item.review_status == "STAGED"
    assert item.human_decision is None
    assert item.registry_action == "NONE"
    assert item.blockers


def test_review_queue_payload_is_stage_only_and_never_targets_registry() -> None:
    investigation = result(diff=-1.0)
    investigation.opening_stock_wms = 0.0
    investigation.opening_stock_wme = 1.0
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    payload = build_review_queue_payload(item)

    assert payload["operation"] == "STAGE_ONLY"
    assert payload["target"]["sheet"] == "VALIDARE_CAZURI"
    assert payload["target"]["sheet"] != "REGISTRU_CAZURI"
    assert payload["values"]["Registry_Action"] == "NONE"
    assert payload["authority"] == {
        "registry_mutation_allowed": False,
        "wms_mutation_allowed": False,
        "wme_mutation_allowed": False,
        "human_decision_required": True,
    }


def test_building_review_item_is_read_only_on_investigation() -> None:
    investigation = result(diff=-1.0)
    investigation.opening_stock_wms = 0.0
    investigation.opening_stock_wme = 1.0
    before = asdict(investigation)
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)

    _ = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    assert asdict(investigation) == before


def test_queue_values_keep_human_fields_empty_until_manual_review() -> None:
    investigation = result(diff=0.001)
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    values = review_queue_values(item)

    assert assessment.status == "TOLERANCE_MATCH"
    assert values["Reviewer"] is None
    assert values["Review_Status"] == "STAGED"
    assert values["Decizie_umana"] is None
    assert values["Reviewed_at"] is None
    assert values["Registry_Action"] == "NONE"



def test_approved_decision_only_proposes_registry_action() -> None:
    investigation = result(diff=-1.0)
    investigation.opening_stock_wms = 0.0
    investigation.opening_stock_wme = 1.0
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    decided = apply_human_review_decision(
        item,
        decision="APROBAT",
        reviewer="Cezar",
        reason="Documentele sustin integral OPEN-01.",
        reviewed_at="2026-10-07T18:30:00+00:00",
    )

    assert decided.review_status == "APPROVED"
    assert decided.registry_action == "PROPOSE_ONLY"
    assert decided.human_decision == "APROBAT"
    assert decided.reviewer == "Cezar"
    assert item.review_status == "STAGED"
    assert item.registry_action == "NONE"


def test_hold_item_cannot_be_approved() -> None:
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
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    try:
        apply_human_review_decision(
            item,
            decision="APROBAT",
            reviewer="Cezar",
            reason="Nu ar trebui acceptat.",
        )
    except ValueError as exc:
        assert "ELIGIBLE_FOR_HUMAN_REVIEW" in str(exc)
    else:
        raise AssertionError("HOLD item was incorrectly approved")


def test_needs_documents_moves_to_hold_without_registry_action() -> None:
    investigation = result(diff=-1.0)
    investigation.opening_stock_wms = 0.0
    investigation.opening_stock_wme = 1.0
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    decided = apply_human_review_decision(
        item,
        decision="NECESITA_DOCUMENTE",
        reviewer="Cezar",
        reason="Lipseste documentul justificativ.",
        reviewed_at="2026-10-07T18:30:00+00:00",
    )

    assert decided.review_status == "HOLD"
    assert decided.registry_action == "NONE"
    assert decided.human_decision == "NECESITA_DOCUMENTE"


def test_rejected_decision_never_proposes_registry_action() -> None:
    investigation = result(diff=-1.0)
    investigation.opening_stock_wms = 0.0
    investigation.opening_stock_wme = 1.0
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    decided = apply_human_review_decision(
        item,
        decision="RESPINS",
        reviewer="Cezar",
        reason="Cauza propusa nu este sustinuta documentar.",
    )

    assert decided.review_status == "REJECTED"
    assert decided.registry_action == "NONE"



def test_tolerance_match_can_be_approved_without_registry_proposal() -> None:
    investigation = result(diff=0.001)
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    decided = apply_human_review_decision(
        item,
        decision="APROBAT",
        reviewer="Cezar",
        reason="Toleranta numerica verificata si acceptata.",
        reviewed_at="2026-10-07T18:45:00+00:00",
    )

    assert assessment.status == "TOLERANCE_MATCH"
    assert decided.review_status == "APPROVED"
    assert decided.human_decision == "APROBAT"
    assert decided.registry_action == "NONE"


def test_hold_still_cannot_be_approved_after_tolerance_extension() -> None:
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
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    try:
        apply_human_review_decision(
            item,
            decision="APROBAT",
            reviewer="Cezar",
            reason="Nu trebuie permis.",
        )
    except ValueError as exc:
        assert "manual evidence VERIFIED" in str(exc)
    else:
        raise AssertionError("HOLD item was incorrectly approved")



def test_hold_can_be_approved_only_after_verified_manual_evidence() -> None:
    investigation = result(
        diff=-8620.2,
        details={},
    )
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(investigation, explanation)
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        evidence_url="https://example.invalid/baseline",
        staged_at="2026-10-07T18:00:00+00:00",
    )

    assert item.promotion_status == "HOLD"
    assert item.blockers == ("AUTO_EXPLAIN_NOT_EXACT",)

    resolved = record_manual_evidence_resolution(
        item,
        evidence_level="A",
        residual=0.0,
        evidence_url="https://example.invalid/manual-report",
        reviewer="Cezar",
        reason="Raport documentar demonstreaza integral diferenta.",
        resolved_blockers=item.blockers,
        verified_at="2026-10-07T20:00:00+00:00",
    )

    assert resolved.promotion_status == "HOLD"
    assert resolved.auto_explain_status == item.auto_explain_status
    assert resolved.manual_evidence_status == "VERIFIED"
    assert resolved.review_status == "IN_REVIEW"
    assert resolved.registry_action == "NONE"

    decided = apply_human_review_decision(
        resolved,
        decision="APROBAT",
        reviewer="Cezar",
        reason="Dovezile manuale nivel A au fost validate.",
        reviewed_at="2026-10-07T20:05:00+00:00",
    )

    assert decided.review_status == "APPROVED"
    assert decided.registry_action == "PROPOSE_ONLY"


def test_manual_evidence_requires_all_original_blockers_and_zero_residual() -> None:
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
    item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        staged_at="2026-10-07T18:00:00+00:00",
    )

    try:
        record_manual_evidence_resolution(
            item,
            evidence_level="A",
            residual=0.5,
            evidence_url="https://example.invalid/manual-report",
            reviewer="Cezar",
            reason="Rezidualul nu este inchis.",
            resolved_blockers=item.blockers,
        )
    except ValueError as exc:
        assert "rezidual zero" in str(exc)
    else:
        raise AssertionError("Manual evidence with non-zero residual was accepted")

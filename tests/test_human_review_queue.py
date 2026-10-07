from __future__ import annotations

from dataclasses import asdict

from traceai_reconciliation.investigation.auto_explain import (
    auto_explanation_from_investigation,
)
from traceai_reconciliation.investigation.human_review_queue import (
    build_human_review_queue_item,
    build_review_queue_payload,
    review_queue_values,
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

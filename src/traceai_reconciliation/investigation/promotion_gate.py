from __future__ import annotations

from dataclasses import dataclass

from .auto_explain import AutoExplanation
from .models import ProductInvestigationResult


@dataclass(frozen=True, slots=True)
class PromotionAssessment:
    """Read-only safety assessment for promoting a shadow explanation."""

    status: str
    eligible_for_review: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    explanation_status: str
    evidence_level: str
    rules: tuple[str, ...]


def assess_auto_explain_promotion(
    result: ProductInvestigationResult,
    explanation: AutoExplanation,
    *,
    tolerance: float = 0.001,
) -> PromotionAssessment:
    """
    Decide whether an EXACT shadow explanation is safe enough to enter human
    promotion review.

    This gate never mutates the investigation, registry, WMS or WME. It is
    intentionally stricter than Auto Explain: mathematical closure is necessary
    but not sufficient when competing residual families remain unresolved.
    """
    blockers: list[str] = []
    warnings: list[str] = []

    if explanation.status != "EXACT":
        blockers.append("AUTO_EXPLAIN_NOT_EXACT")
        return PromotionAssessment(
            status="HOLD",
            eligible_for_review=False,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            explanation_status=explanation.status,
            evidence_level=explanation.evidence_level,
            rules=explanation.rules,
        )

    if (
        abs(float(result.initial_difference)) <= tolerance
        and not explanation.components
    ):
        return PromotionAssessment(
            status="TOLERANCE_MATCH",
            eligible_for_review=True,
            blockers=(),
            warnings=("NO_CAUSAL_RULE_REQUIRED_WITHIN_TOLERANCE",),
            explanation_status=explanation.status,
            evidence_level=explanation.evidence_level,
            rules=explanation.rules,
        )

    if explanation.evidence_level != "A":
        blockers.append(
            f"EVIDENCE_LEVEL_{explanation.evidence_level}_REQUIRES_HUMAN_VALIDATION"
        )

    details = result.details or {}
    rules = set(explanation.rules)
    component_sources = {
        str(component.source)
        for component in explanation.components
        if component.contributes
    }

    production = details.get("production_matching", {}) or {}
    production_doc_residual = abs(
        float(production.get("document_residual_total", 0.0) or 0.0)
    )
    production_owned = (
        "PROD-02" in rules
        or any(
            source.startswith("production_matching")
            for source in component_sources
        )
    )
    if production_doc_residual > tolerance and not production_owned:
        blockers.append("UNRESOLVED_PRODUCTION_DOCUMENT_RESIDUAL")

    production_input = details.get("production_input_matching", {}) or {}
    production_input_residual = abs(
        float(
            production_input.get(
                "persistent_residual_total",
                production_input.get("residual_total", 0.0),
            )
            or 0.0
        )
    )
    if production_input_residual > tolerance and "PROD-03" not in rules:
        blockers.append("UNRESOLVED_PRODUCTION_INPUT_RESIDUAL")

    delivery = details.get("delivery_matching", {}) or {}
    delivery_residual = abs(
        float(delivery.get("residual_total", 0.0) or 0.0)
    )
    if delivery_residual > tolerance and "DEL-02" not in rules:
        blockers.append("UNRESOLVED_DELIVERY_RESIDUAL")

    generic = details.get("generic_stock_corrections", {}) or {}
    generic_residual = abs(
        float(generic.get("residual_total", 0.0) or 0.0)
    )
    generic_owned = any(
        component.rule_id == "ADJ-01"
        and str(component.source).startswith("generic_stock_corrections")
        for component in explanation.components
        if component.contributes
    )
    if generic_residual > tolerance and not generic_owned:
        blockers.append("UNRESOLVED_GENERIC_STOCK_CORRECTION")

    special = details.get("special_status_matching", {}) or {}
    special_residual_count = int(
        special.get("residual_corrections", 0) or 0
    )
    if special_residual_count > 0 and "GST-04" not in rules:
        blockers.append("UNRESOLVED_SPECIAL_STATUS_CORRECTION")

    stock_zone = details.get("stock_report_zone_matching", {}) or {}
    unresolved_zone_rows = int(stock_zone.get("unresolved_rows", 0) or 0)
    if unresolved_zone_rows > 0:
        blockers.append("UNRESOLVED_STOCK_REPORT_ZONE_MAPPING")

    if "WME-02" in rules:
        wme_residual = details.get("wme_residual_movements", {}) or {}
        movements = list(wme_residual.get("movements", []) or [])
        pv_count = sum(
            1
            for item in movements
            if str(item.get("operation_type", "")).strip().upper() == "PV"
        )
        if pv_count > 1:
            warnings.append("WME02_MULTIPLE_PV_EVENTS_REQUIRE_REVIEW")

    unmatched_count = len(result.unmatched_operations or [])
    if unmatched_count:
        warnings.append(f"UNMATCHED_OPERATIONS_{unmatched_count}")

    if result.technical_warnings:
        warnings.append(
            f"TECHNICAL_WARNINGS_{len(result.technical_warnings)}"
        )

    eligible = not blockers
    return PromotionAssessment(
        status="ELIGIBLE_FOR_HUMAN_REVIEW" if eligible else "HOLD",
        eligible_for_review=eligible,
        blockers=tuple(dict.fromkeys(blockers)),
        warnings=tuple(dict.fromkeys(warnings)),
        explanation_status=explanation.status,
        evidence_level=explanation.evidence_level,
        rules=explanation.rules,
    )

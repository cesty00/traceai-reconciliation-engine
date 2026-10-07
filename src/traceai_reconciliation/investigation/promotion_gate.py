from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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


def _parse_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text or text == "-":
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d.%m.%Y",
    ):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _movement_totals_are_balanced(
    result: ProductInvestigationResult,
    *,
    tolerance: float,
) -> bool:
    details = result.details or {}
    wms = details.get("wms_net_movement")
    wme = details.get("wme_net_movement")
    if wms is None or wme is None:
        return False
    try:
        return abs(float(wms) - float(wme)) <= tolerance
    except (TypeError, ValueError):
        return False


def _generic_corrections_are_absorbed_by_prod03(
    result: ProductInvestigationResult,
    production_input: dict,
    *,
    tolerance: float,
) -> bool:
    checkpoint = _parse_datetime(
        production_input.get("inventory_checkpoint_date")
    )

    neutralizers: list[tuple[datetime | None, float]] = []
    for item in list(
        production_input.get("neutralized_residual_documents", []) or []
    ):
        correction = item.get("neutralizing_correction") or {}
        if not correction:
            continue
        try:
            quantity = float(correction.get("quantity", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        neutralizers.append(
            (_parse_datetime(correction.get("date")), quantity)
        )

    generic_ops = [
        item
        for item in list(result.unmatched_operations or [])
        if str(item.get("system", "")).strip().upper() == "WMS"
        and str(item.get("operation_type", "")).strip().upper() == "COR STOC"
        and str(item.get("status", "")).strip().upper() == "WMS_ONLY_REVIEW"
    ]
    if not generic_ops:
        return False

    for item in generic_ops:
        item_date = _parse_datetime(item.get("date"))
        try:
            item_qty = float(item.get("quantity", 0.0) or 0.0)
        except (TypeError, ValueError):
            return False

        if (
            checkpoint is not None
            and item_date is not None
            and item_date <= checkpoint
        ):
            continue

        matched_neutralizer = False
        for neutralizer_date, neutralizer_qty in neutralizers:
            same_quantity = abs(item_qty - neutralizer_qty) <= tolerance
            same_day = (
                item_date is None
                or neutralizer_date is None
                or item_date.date() == neutralizer_date.date()
            )
            if same_quantity and same_day:
                matched_neutralizer = True
                break
        if matched_neutralizer:
            continue

        return False

    return True


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

    movement_balanced = _movement_totals_are_balanced(
        result,
        tolerance=tolerance,
    )

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
    generic_noncompeting = False
    if (
        generic_residual > tolerance
        and not generic_owned
        and "PROD-03" in rules
        and _generic_corrections_are_absorbed_by_prod03(
            result,
            production_input,
            tolerance=tolerance,
        )
    ):
        generic_noncompeting = True
        warnings.append(
            "GENERIC_CORRECTIONS_ABSORBED_BY_PROD03_CHECKPOINT"
        )

    special = details.get("special_status_matching", {}) or {}
    special_residual_count = int(
        special.get("residual_corrections", 0) or 0
    )
    if special_residual_count > 0 and "GST-04" not in rules:
        blockers.append("UNRESOLVED_SPECIAL_STATUS_CORRECTION")

    stock_zone = details.get("stock_report_zone_matching", {}) or {}
    unresolved_zone_rows = int(stock_zone.get("unresolved_rows", 0) or 0)
    mapping_effect = float(
        stock_zone.get("mapping_effect_total", 0.0) or 0.0
    )
    exact_report_mapping = (
        "GST-02/GST-03" in rules
        and abs(mapping_effect - float(result.initial_difference)) <= tolerance
    )

    if (
        generic_residual > tolerance
        and not generic_owned
        and not generic_noncompeting
    ):
        if movement_balanced and exact_report_mapping:
            generic_noncompeting = True
            warnings.append(
                "GENERIC_CORRECTIONS_NONCOMPETING_SYSTEM_MOVEMENTS_BALANCED"
            )
        else:
            blockers.append("UNRESOLVED_GENERIC_STOCK_CORRECTION")

    if unresolved_zone_rows > 0:
        if movement_balanced and exact_report_mapping:
            warnings.append(
                "UNMAPPED_STOCK_ZONE_NONCOMPETING_SYSTEM_MOVEMENTS_BALANCED"
            )
        else:
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

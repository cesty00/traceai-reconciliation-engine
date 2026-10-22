from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from traceai_reconciliation.version import OPERATOR_OUTPUT_SCHEMA_VERSION

from .auto_explain import AutoExplanation
from .models import ProductInvestigationResult
from .promotion_gate import PromotionAssessment


REQUIRED_OPERATOR_FIELDS = (
    "schema_version",
    "case_id",
    "product_code",
    "product_name",
    "unit",
    "difference",
    "cause",
    "cause_status",
    "evidence_level",
    "rules",
    "correction_target",
    "operator_action",
    "operator_status",
    "residual",
    "evidence",
    "blockers",
    "warnings",
    "wms_mutation_allowed",
    "wme_mutation_allowed",
)


@dataclass(frozen=True, slots=True)
class DailyOperatorResult:
    """Compact, read-only result for daily operational reconciliation."""

    schema_version: str
    case_id: str
    product_code: str
    product_name: str
    unit: str
    difference: float
    cause: str
    cause_status: str
    evidence_level: str
    rules: tuple[str, ...]
    correction_target: str
    operator_action: str
    operator_status: str
    residual: float
    evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    wms_mutation_allowed: bool = False
    wme_mutation_allowed: bool = False
    technical_receipts: tuple[dict[str, Any], ...] = ()


def _contributing_evidence(explanation: AutoExplanation) -> tuple[str, ...]:
    evidence: list[str] = []
    for item in explanation.components:
        if not item.contributes:
            continue
        text = (
            f"{item.rule_id}: {item.description} "
            f"(efect {float(item.effect):.3f}; sursa {item.source or '-'})"
        )
        evidence.append(text)
    return tuple(evidence)


def _action_for_rules(
    *,
    rules: tuple[str, ...],
    assessment: PromotionAssessment,
    result: ProductInvestigationResult,
) -> tuple[str, str, str]:
    if assessment.status == "HOLD":
        blockers = ", ".join(assessment.blockers) or "dovezi insuficiente"
        return (
            "REVIEW",
            "Nu corecta stocul inca. Rezolva mai intai: " + blockers + ".",
            "REVIEW",
        )

    rule_set = set(rules)

    if rule_set and rule_set.issubset({"GST-02", "GST-03", "GST-04"}):
        return (
            "REPORT_MAPPING",
            (
                "Nu modifica stocul WMS/WME. Verifica si corecteaza maparea/scope-ul "
                "raportului pentru gestiunea indicata de dovezi."
            ),
            "CONFIRMAT" if assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW" else "REVIEW",
        )

    if "OPEN-01" in rule_set:
        return (
            "OPENING_BALANCE",
            (
                "Reconciliaza soldul initial WMS versus WME. Corecteaza operational "
                "numai dupa confirmarea documentului de deschidere; nu genera ajustare "
                "automata."
            ),
            "CONFIRMAT" if assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW" else "REVIEW",
        )

    if any(rule.startswith("PROD-") for rule in rule_set):
        return (
            "WMS_WME_DOCUMENT_FLOW",
            (
                "Verifica documentele de productie indicate de motor (BC/NP/transfer). "
                "Corecteaza sistemul in care documentul lipseste sau este diferit numai "
                "dupa confirmarea documentului sursa."
            ),
            "CONFIRMAT" if assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW" else "REVIEW",
        )

    if "ADJ-01" in rule_set:
        return (
            "STOCK_ADJUSTMENT",
            (
                "Verifica documentul de ajustare/correctie stoc indicat de motor si "
                "alinierea lui intre WMS si WME. Nu replica automat ajustarea."
            ),
            "CONFIRMAT" if assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW" else "REVIEW",
        )

    recommendation = ""
    if result.recommendations:
        first = result.recommendations[0]
        recommendation = str(
            first.get("action")
            or first.get("recommendation")
            or first.get("description")
            or ""
        ).strip()

    return (
        "REVIEW",
        recommendation
        or (
            "Verifica operatiunile si documentele indicate de motor; corecteaza "
            "operational numai dupa confirmarea dovezii."
        ),
        "REVIEW",
    )


def build_daily_operator_result(
    result: ProductInvestigationResult,
    explanation: AutoExplanation,
    assessment: PromotionAssessment,
) -> DailyOperatorResult:
    """Translate the technical investigation into a compact operator-facing view.

    The view is advisory and read-only. It never authorizes or performs a WMS/WME
    mutation.
    """

    rules = tuple(explanation.rules)
    correction_target, operator_action, operator_status = _action_for_rules(
        rules=rules,
        assessment=assessment,
        result=result,
    )

    evidence = _contributing_evidence(explanation)
    if not evidence and result.findings:
        evidence = tuple(
            str(
                item.get("description")
                or item.get("finding")
                or item.get("message")
                or item
            )
            for item in result.findings[:5]
        )

    return DailyOperatorResult(
        schema_version=OPERATOR_OUTPUT_SCHEMA_VERSION,
        case_id=result.case_id,
        product_code=result.product_code,
        product_name=result.product_name,
        unit=result.unit,
        difference=float(explanation.initial_difference),
        cause=result.cause_description,
        cause_status=result.cause_status,
        evidence_level=explanation.evidence_level,
        rules=rules,
        correction_target=correction_target,
        operator_action=operator_action,
        operator_status=operator_status,
        residual=float(explanation.residual_difference),
        evidence=evidence,
        blockers=tuple(assessment.blockers),
        warnings=tuple(assessment.warnings),
        technical_receipts=tuple(
            dict(item)
            for item in result.details.get('operator_receipt_classification', [])
            if isinstance(item, dict)
        ),
    )


def validate_daily_operator_contract(
    payload: dict[str, object],
) -> tuple[str, ...]:
    errors: list[str] = []
    if payload.get("schema_version") != OPERATOR_OUTPUT_SCHEMA_VERSION:
        errors.append(
            "schema_version:"
            f"expected={OPERATOR_OUTPUT_SCHEMA_VERSION}:"
            f"actual={payload.get('schema_version')}"
        )
    for field in REQUIRED_OPERATOR_FIELDS:
        if field not in payload:
            errors.append(f"missing:{field}")
    if "technical_receipts" in payload:
        receipts = payload["technical_receipts"]
        if not isinstance(receipts, list):
            errors.append("invalid:technical_receipts")
        else:
            for item in receipts:
                if not isinstance(item, dict):
                    errors.append("invalid:technical_receipt_item")
                    continue
                if item.get("family") not in {"RETURN_IN", "RECEIPT_UNCLASSIFIED"}:
                    errors.append("invalid:technical_receipt_family")
                if item.get("status") not in {"MATCH", "QTY_DIFF", "REVIEW"}:
                    errors.append("invalid:technical_receipt_status")
    for field in ("rules", "evidence", "blockers", "warnings"):
        if not isinstance(payload.get(field), list):
            errors.append(f"invalid:{field}")
    if payload.get("wms_mutation_allowed") is not False:
        errors.append("authority:wms_mutation_allowed")
    if payload.get("wme_mutation_allowed") is not False:
        errors.append("authority:wme_mutation_allowed")
    return tuple(errors)


def daily_operator_result_to_dict(
    result: DailyOperatorResult,
) -> dict[str, object]:
    payload = asdict(result)
    payload["rules"] = list(result.rules)
    payload["evidence"] = list(result.evidence)
    payload["blockers"] = list(result.blockers)
    payload["warnings"] = list(result.warnings)
    payload["technical_receipts"] = [dict(item) for item in result.technical_receipts]
    violations = validate_daily_operator_contract(payload)
    if violations:
        raise ValueError(
            "daily operator contract violation: " + ", ".join(violations)
        )
    return payload

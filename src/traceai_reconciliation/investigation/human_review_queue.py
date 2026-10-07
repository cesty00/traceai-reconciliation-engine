from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any

from .auto_explain import AutoExplanation
from .models import ProductInvestigationResult
from .promotion_gate import PromotionAssessment


REVIEW_QUEUE_COLUMNS = [
    "QUEUE_ID",
    "CASE_ID",
    "Cod_produs",
    "Diferenta",
    "AutoExplain_Status",
    "Nivel_proba",
    "Reguli_propuse",
    "Promotion_Status",
    "Blockers",
    "Warnings",
    "Prioritate",
    "Ce_se_valideaza",
    "Link_dovezi",
    "Staged_at",
    "Execution_ID",
    "Reviewer",
    "Review_Status",
    "Decizie_umana",
    "Motiv_decizie",
    "Reviewed_at",
    "Registry_Action",
]


@dataclass(frozen=True, slots=True)
class HumanReviewQueueItem:
    queue_id: str
    case_id: str
    product_code: str
    difference: float
    auto_explain_status: str
    evidence_level: str
    proposed_rules: tuple[str, ...]
    promotion_status: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    priority: str
    validation_prompt: str
    evidence_url: str | None
    staged_at: str
    execution_id: str | None
    reviewer: str | None = None
    review_status: str = "STAGED"
    human_decision: str | None = None
    decision_reason: str | None = None
    reviewed_at: str | None = None
    registry_action: str = "NONE"


def _priority(
    result: ProductInvestigationResult,
    assessment: PromotionAssessment,
) -> str:
    if assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW":
        return "P1"
    if assessment.status == "TOLERANCE_MATCH":
        return "P2"
    if result.evidence_level == "A":
        return "P2"
    return "P3"


def _validation_prompt(
    explanation: AutoExplanation,
    assessment: PromotionAssessment,
) -> str:
    if assessment.status == "ELIGIBLE_FOR_HUMAN_REVIEW":
        rules = ", ".join(explanation.rules) or "-"
        return (
            "Valideaza documentar componentele Auto Explain si confirma daca "
            f"regulile {rules} reprezinta cauza acceptata a diferentei. "
            "Aprobarea nu autorizeaza automat update REGISTRU/WMS/WME."
        )

    if assessment.status == "TOLERANCE_MATCH":
        return (
            "Confirma toleranta numerica si absenta unei diferente operationale "
            "materiale. Nu genera ajustare de stoc."
        )

    blockers = ", ".join(assessment.blockers) or "necunoscut"
    return (
        "Caz HOLD. Rezolva mai intai blocker-ele Promotion Safety Gate: "
        f"{blockers}. Nu aproba promovarea pana la inchiderea lor."
    )


def build_human_review_queue_item(
    result: ProductInvestigationResult,
    explanation: AutoExplanation,
    assessment: PromotionAssessment,
    *,
    evidence_url: str | None = None,
    execution_id: str | None = None,
    staged_at: str | None = None,
) -> HumanReviewQueueItem:
    """
    Build one deterministic, read-only human-review work item.

    Authority contract:
    - this does not modify ProductInvestigationResult;
    - this does not modify REGISTRU_CAZURI;
    - this does not modify WMS/WME;
    - APPROVED/REJECTED decisions belong to a later human step.
    """
    timestamp = staged_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    queue_id = f"HR-{result.case_id}"

    return HumanReviewQueueItem(
        queue_id=queue_id,
        case_id=result.case_id,
        product_code=result.product_code,
        difference=float(result.initial_difference),
        auto_explain_status=explanation.status,
        evidence_level=explanation.evidence_level,
        proposed_rules=tuple(explanation.rules),
        promotion_status=assessment.status,
        blockers=tuple(assessment.blockers),
        warnings=tuple(assessment.warnings),
        priority=_priority(result, assessment),
        validation_prompt=_validation_prompt(explanation, assessment),
        evidence_url=evidence_url,
        staged_at=timestamp,
        execution_id=execution_id,
    )


def review_queue_values(
    item: HumanReviewQueueItem,
) -> dict[str, Any]:
    return {
        "QUEUE_ID": item.queue_id,
        "CASE_ID": item.case_id,
        "Cod_produs": item.product_code,
        "Diferenta": item.difference,
        "AutoExplain_Status": item.auto_explain_status,
        "Nivel_proba": item.evidence_level,
        "Reguli_propuse": ", ".join(item.proposed_rules) or None,
        "Promotion_Status": item.promotion_status,
        "Blockers": ", ".join(item.blockers) or None,
        "Warnings": ", ".join(item.warnings) or None,
        "Prioritate": item.priority,
        "Ce_se_valideaza": item.validation_prompt,
        "Link_dovezi": item.evidence_url,
        "Staged_at": item.staged_at,
        "Execution_ID": item.execution_id,
        "Reviewer": item.reviewer,
        "Review_Status": item.review_status,
        "Decizie_umana": item.human_decision,
        "Motiv_decizie": item.decision_reason,
        "Reviewed_at": item.reviewed_at,
        "Registry_Action": item.registry_action,
    }


def build_review_queue_payload(
    item: HumanReviewQueueItem,
) -> dict[str, Any]:
    """
    Return a portable STAGE_ONLY payload for VALIDARE_CAZURI.

    No apply helper is intentionally provided in v0.7 phase 1.
    """
    return {
        "schema_version": "0.7.0",
        "target": {
            "spreadsheet": "CONTROL_RECONCILIERE_WMS_WME",
            "sheet": "VALIDARE_CAZURI",
        },
        "operation": "STAGE_ONLY",
        "lookup": {
            "primary": {
                "QUEUE_ID": item.queue_id,
            },
            "fallback": {
                "CASE_ID": item.case_id,
            },
        },
        "columns": REVIEW_QUEUE_COLUMNS,
        "values": review_queue_values(item),
        "authority": {
            "registry_mutation_allowed": False,
            "wms_mutation_allowed": False,
            "wme_mutation_allowed": False,
            "human_decision_required": True,
        },
    }


def queue_item_to_dict(
    item: HumanReviewQueueItem,
) -> dict[str, Any]:
    payload = asdict(item)
    payload["proposed_rules"] = list(item.proposed_rules)
    payload["blockers"] = list(item.blockers)
    payload["warnings"] = list(item.warnings)
    return payload



def apply_human_review_decision(
    item: HumanReviewQueueItem,
    *,
    decision: str,
    reviewer: str,
    reason: str,
    reviewed_at: str | None = None,
) -> HumanReviewQueueItem:
    """
    Record one explicit human decision in the review queue.

    This function changes only the immutable queue item returned to the caller.
    It never writes REGISTRU_CAZURI, WMS or WME.

    APPROVED is allowed only for ELIGIBLE_FOR_HUMAN_REVIEW items.
    Even then, Registry_Action becomes PROPOSE_ONLY, never APPLY.
    """
    decision_normalized = decision.strip().upper()
    reviewer_clean = reviewer.strip()
    reason_clean = reason.strip()
    if not reviewer_clean:
        raise ValueError("Reviewer este obligatoriu.")
    if not reason_clean:
        raise ValueError("Motiv_decizie este obligatoriu.")

    allowed = {"APROBAT", "RESPINS", "NECESITA_DOCUMENTE"}
    if decision_normalized not in allowed:
        raise ValueError(
            "Decizie_umana trebuie sa fie APROBAT, RESPINS sau "
            "NECESITA_DOCUMENTE."
        )

    timestamp = reviewed_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    if decision_normalized == "APROBAT":
        if item.promotion_status != "ELIGIBLE_FOR_HUMAN_REVIEW":
            raise ValueError(
                "APROBAT este permis numai pentru "
                "ELIGIBLE_FOR_HUMAN_REVIEW."
            )
        review_status = "APPROVED"
        registry_action = "PROPOSE_ONLY"
    elif decision_normalized == "RESPINS":
        review_status = "REJECTED"
        registry_action = "NONE"
    else:
        review_status = "HOLD"
        registry_action = "NONE"

    return replace(
        item,
        reviewer=reviewer_clean,
        review_status=review_status,
        human_decision=decision_normalized,
        decision_reason=reason_clean,
        reviewed_at=timestamp,
        registry_action=registry_action,
    )

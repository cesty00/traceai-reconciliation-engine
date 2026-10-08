from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from traceai_reconciliation import __version__
from traceai_reconciliation.reports import generate_docx_report

from .auto_explain import (
    auto_explanation_from_investigation,
    auto_explanation_to_dict,
)
from .case_builder import build_case_report
from .engine import investigate_product
from .human_review_queue import (
    build_human_review_queue_item,
    build_review_queue_payload,
)
from .models import InvestigationSources
from .promotion_gate import assess_auto_explain_promotion
from .registry_sync import build_registry_update


@dataclass(frozen=True, slots=True)
class SourceReadiness:
    ready: bool
    required: tuple[str, ...]
    missing: tuple[str, ...]
    paths: dict[str, str]


@dataclass(frozen=True, slots=True)
class SelfServiceRunResult:
    case_id: str
    product_code: str
    status: str
    next_action: str
    output_dir: str
    technical_json: str
    docx: str
    registry_json: str
    review_queue_json: str
    summary_json: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def validate_source_readiness(
    sources: InvestigationSources,
) -> SourceReadiness:
    paths = {
        "stock_report": Path(sources.stock_report),
        "opening_stock_wms": Path(sources.opening_stock_wms),
        "wms_movements": Path(sources.wms_movements),
        "wme_ledger": Path(sources.wme_ledger),
        "production": Path(sources.production),
        "nomenclature": Path(sources.nomenclature),
    }
    missing = tuple(
        name
        for name, path in paths.items()
        if not path.exists() or not path.is_file()
    )
    readiness = SourceReadiness(
        ready=not missing,
        required=tuple(paths),
        missing=missing,
        paths={name: str(path) for name, path in paths.items()},
    )
    if missing:
        raise FileNotFoundError(
            "Self-service source readiness failed. Missing required sources: "
            + ", ".join(missing)
        )
    return readiness


def _next_action(promotion_status: str) -> str:
    if promotion_status == "ELIGIBLE_FOR_HUMAN_REVIEW":
        return "HUMAN_REVIEW"
    if promotion_status == "TOLERANCE_MATCH":
        return "HUMAN_REVIEW_TOLERANCE"
    return "RESOLVE_PROMOTION_BLOCKERS"


def run_self_service_case(
    *,
    product_code: str,
    period: str,
    sources: InvestigationSources,
    output_dir: str | Path,
    case_id: str | None = None,
    report_date: str | None = None,
    rules_version: str = "0.4",
    engine_commit_sha: str = "LOCAL_OR_UNSET",
    execution_id: str | None = None,
    staged_at: str | None = None,
    evidence_url: str | None = None,
) -> SelfServiceRunResult:
    """
    Run one product investigation end-to-end and stage a review payload.

    Authority boundary:
    - never approves a case;
    - never applies REGISTRU_CAZURI changes;
    - never mutates WMS/WME;
    - never converts HOLD into an approved state.
    """
    product = str(product_code).strip()
    if not product:
        raise ValueError("product_code este obligatoriu.")
    if not str(period).strip():
        raise ValueError("period este obligatoriu.")

    resolved_case_id = (
        str(case_id).strip()
        if case_id and str(case_id).strip()
        else f"CASE-SELF-{product}"
    )
    root = Path(output_dir)
    case_dir = root / resolved_case_id.replace("/", "_")
    case_dir.mkdir(parents=True, exist_ok=True)

    readiness = validate_source_readiness(sources)
    effective_sources = replace(
        sources,
        cache_dir=sources.cache_dir or (root / ".traceai_cache"),
        use_source_index=True,
    )

    investigation = investigate_product(
        product_code=product,
        case_id=resolved_case_id,
        sources=effective_sources,
        period=period,
        report_date=report_date,
    )
    case_report = build_case_report(
        investigation,
        engine_version=__version__,
        engine_commit_sha=engine_commit_sha,
        rules_version=rules_version,
        execution_id=execution_id,
    )
    explanation = auto_explanation_from_investigation(investigation)
    assessment = assess_auto_explain_promotion(
        investigation,
        explanation,
    )
    registry_update = build_registry_update(
        investigation,
        case_report,
    )

    technical_json = case_dir / "case.json"
    docx = case_dir / "case.docx"
    registry_json = case_dir / "registry_update.json"
    review_queue_json = case_dir / "review_queue.json"
    summary_json = case_dir / "self_service_summary.json"

    generate_docx_report(case_report, docx)

    queue_item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        evidence_url=evidence_url or str(docx),
        execution_id=execution_id,
        staged_at=staged_at,
    )
    review_payload = build_review_queue_payload(queue_item)

    technical_payload = {
        "investigation": asdict(investigation),
        "case_report": asdict(case_report),
        "auto_explain": auto_explanation_to_dict(explanation),
        "promotion_assessment": asdict(assessment),
        "source_readiness": asdict(readiness),
        "authority": {
            "human_decision_required": True,
            "registry_apply_allowed": False,
            "wms_mutation_allowed": False,
            "wme_mutation_allowed": False,
        },
    }
    _write_json(technical_json, technical_payload)
    _write_json(registry_json, registry_update)
    _write_json(review_queue_json, review_payload)

    next_action = _next_action(assessment.status)
    summary = {
        "schema_version": "0.8.0",
        "generated_at": staged_at or _utc_now(),
        "engine_version": __version__,
        "rules_version": rules_version,
        "engine_commit_sha": engine_commit_sha,
        "case_id": resolved_case_id,
        "product_code": product,
        "period": period,
        "verdict": case_report.verdict,
        "evidence_level": explanation.evidence_level,
        "initial_difference": explanation.initial_difference,
        "explained_difference": explanation.explained_difference,
        "residual_difference": explanation.residual_difference,
        "auto_explain_status": explanation.status,
        "promotion_status": assessment.status,
        "blockers": list(assessment.blockers),
        "warnings": list(assessment.warnings),
        "review_status": queue_item.review_status,
        "registry_action": queue_item.registry_action,
        "next_action": next_action,
        "outputs": {
            "case_json": str(technical_json),
            "case_docx": str(docx),
            "registry_update_json": str(registry_json),
            "review_queue_json": str(review_queue_json),
        },
        "authority": {
            "human_decision_required": True,
            "automatic_approval_allowed": False,
            "registry_apply_allowed": False,
            "wms_mutation_allowed": False,
            "wme_mutation_allowed": False,
        },
    }
    _write_json(summary_json, summary)

    return SelfServiceRunResult(
        case_id=resolved_case_id,
        product_code=product,
        status=assessment.status,
        next_action=next_action,
        output_dir=str(case_dir),
        technical_json=str(technical_json),
        docx=str(docx),
        registry_json=str(registry_json),
        review_queue_json=str(review_queue_json),
        summary_json=str(summary_json),
    )

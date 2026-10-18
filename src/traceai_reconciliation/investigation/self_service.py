from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from traceai_reconciliation import __version__
from traceai_reconciliation.reports import generate_docx_report
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx
from traceai_reconciliation.version import (
    SELF_SERVICE_BATCH_SCHEMA_VERSION,
    SELF_SERVICE_SUMMARY_SCHEMA_VERSION,
)

from .auto_explain import (
    auto_explanation_from_investigation,
    auto_explanation_to_dict,
)
from .case_builder import build_case_report
from .daily_operator import build_daily_operator_result, daily_operator_result_to_dict
from .engine import investigate_product
from .human_evidence import HumanAttestation, applicable_attestations
from .human_review_queue import (
    build_human_review_queue_item,
    build_review_queue_payload,
)
from .models import InvestigationSources
from .promotion_gate import assess_auto_explain_promotion
from .registry_sync import build_registry_update
from .source_hash_cache import hash_sources
from .source_readers import parse_period


@dataclass(frozen=True, slots=True)
class SourceReadiness:
    ready: bool
    required: tuple[str, ...]
    missing: tuple[str, ...]
    empty: tuple[str, ...]
    invalid_format: tuple[str, ...]
    paths: dict[str, str]
    file_sizes: dict[str, int]
    source_hashes: dict[str, str]
    period: str | None = None


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
    operator_json: str | None = None


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
    *,
    period: str | None = None,
) -> SourceReadiness:
    """
    Fail closed before a self-service investigation when required sources are
    missing, empty, have unsupported formats, or the requested period is invalid.

    Source identity is captured with SHA-256 so the later investigation can
    reuse the same hash cache. No source substitution or fuzzy file selection
    is attempted.
    """
    paths = {
        "stock_report": Path(sources.stock_report),
        "opening_stock_wms": Path(sources.opening_stock_wms),
        "wms_movements": Path(sources.wms_movements),
        "wme_ledger": Path(sources.wme_ledger),
        "production": Path(sources.production),
        "nomenclature": Path(sources.nomenclature),
    }
    required_formats = {
        "stock_report": {".xlsx"},
        "opening_stock_wms": {".xlsx", ".csv"},
        "wms_movements": {".csv", ".xlsx"},
        "wme_ledger": {".xlsx"},
        "production": {".csv"},
        "nomenclature": {".xlsx"},
    }

    missing = tuple(
        name
        for name, path in paths.items()
        if not path.exists() or not path.is_file()
    )
    empty = tuple(
        name
        for name, path in paths.items()
        if name not in missing and path.stat().st_size <= 0
    )
    invalid_format = tuple(
        name
        for name, path in paths.items()
        if name not in missing
        and path.suffix.lower() not in required_formats[name]
    )

    if missing:
        raise FileNotFoundError(
            "Self-service source readiness failed. Missing required sources: "
            + ", ".join(missing)
        )
    if empty:
        raise ValueError(
            "Self-service source readiness failed. Empty required sources: "
            + ", ".join(empty)
        )
    if invalid_format:
        raise ValueError(
            "Self-service source readiness failed. Unsupported source formats: "
            + ", ".join(invalid_format)
        )

    normalized_period = str(period).strip() if period is not None else None
    if normalized_period:
        parse_period(normalized_period)

    source_hashes = hash_sources(
        paths,
        cache_dir=sources.cache_dir,
    )

    return SourceReadiness(
        ready=True,
        required=tuple(paths),
        missing=(),
        empty=(),
        invalid_format=(),
        paths={name: str(path) for name, path in paths.items()},
        file_sizes={
            name: int(path.stat().st_size)
            for name, path in paths.items()
        },
        source_hashes=source_hashes,
        period=normalized_period,
    )

REQUIRED_SELF_SERVICE_AUTHORITY_FIELDS = (
    "human_decision_required",
    "automatic_approval_allowed",
    "registry_apply_allowed",
    "wms_mutation_allowed",
    "wme_mutation_allowed",
)


def validate_self_service_summary_contract(
    payload: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []

    if payload.get("schema_version") != SELF_SERVICE_SUMMARY_SCHEMA_VERSION:
        errors.append(
            "schema_version:"
            f"expected={SELF_SERVICE_SUMMARY_SCHEMA_VERSION}:"
            f"actual={payload.get('schema_version')}"
        )

    for field in (
        "generated_at",
        "engine_version",
        "rules_version",
        "engine_commit_sha",
        "case_id",
        "product_code",
        "period",
        "promotion_status",
        "next_action",
        "outputs",
        "authority",
    ):
        if field not in payload:
            errors.append(f"missing:{field}")

    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        errors.append("invalid:outputs")

    authority = payload.get("authority")
    if not isinstance(authority, dict):
        errors.append("invalid:authority")
    else:
        for field in REQUIRED_SELF_SERVICE_AUTHORITY_FIELDS:
            if field not in authority:
                errors.append(f"missing:authority.{field}")
        if authority.get("human_decision_required") is not True:
            errors.append("authority:human_decision_required")
        for field in (
            "automatic_approval_allowed",
            "registry_apply_allowed",
            "wms_mutation_allowed",
            "wme_mutation_allowed",
        ):
            if authority.get(field) is not False:
                errors.append(f"authority:{field}")

    return tuple(errors)


def validate_self_service_batch_contract(
    payload: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []

    if payload.get("schema_version") != SELF_SERVICE_BATCH_SCHEMA_VERSION:
        errors.append(
            "schema_version:"
            f"expected={SELF_SERVICE_BATCH_SCHEMA_VERSION}:"
            f"actual={payload.get('schema_version')}"
        )

    for field in (
        "batch_id",
        "engine_version",
        "rules_version",
        "engine_commit_sha",
        "total_cases",
        "executed",
        "skipped",
        "eligible",
        "tolerance",
        "hold",
        "error",
        "cases",
        "authority",
    ):
        if field not in payload:
            errors.append(f"missing:{field}")

    if not isinstance(payload.get("cases"), list):
        errors.append("invalid:cases")

    authority = payload.get("authority")
    if not isinstance(authority, dict):
        errors.append("invalid:authority")
    else:
        for field in REQUIRED_SELF_SERVICE_AUTHORITY_FIELDS:
            if field not in authority:
                errors.append(f"missing:authority.{field}")
        if authority.get("human_decision_required") is not True:
            errors.append("authority:human_decision_required")
        for field in (
            "automatic_approval_allowed",
            "registry_apply_allowed",
            "wms_mutation_allowed",
            "wme_mutation_allowed",
        ):
            if authority.get(field) is not False:
                errors.append(f"authority:{field}")

    return tuple(errors)


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
    human_attestations: list[HumanAttestation] | None = None,
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

    effective_sources = replace(
        sources,
        cache_dir=sources.cache_dir or (root / ".traceai_cache"),
        use_source_index=sources.use_source_index,
    )
    readiness = validate_source_readiness(
        effective_sources,
        period=period,
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
    # Historical BC evidence uses the full indexed investigation sources,
    # never the narrow Daily delta window. Fail closed on documentary ambiguity.
    if effective_sources.use_source_index and any(
        row.get("step") == "PRODUCTION_INPUT_BC"
        for row in case_report.conclusion_traceability
    ):
        from .bc_index_bridge import attach_bc_from_index
        from .source_index import SQLiteSourceIndex
        mapping_ids = investigation.details.get("wme_mapping_ids", [])
        if len(mapping_ids) != 1:
            raise ValueError("BC evidence requires unique WME product mapping")
        index = SQLiteSourceIndex(effective_sources.cache_dir)
        attach_bc_from_index(case_report, index, str(mapping_ids[0]))

    # Human statements only annotate exactly bound source rows. They do not
    # alter matching, automated explanation, eligibility or the REVIEW verdict.
    verified_human_evidence = applicable_attestations(
        product, case_report.operation_timeline, human_attestations or [],
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
    operator_json = case_dir / "daily_operator_result.json"
    summary_json = case_dir / "self_service_summary.json"

    generate_docx_report(case_report, case_dir / "case_technical.docx")
    generate_operator_causes_docx(case_report, docx, details=investigation.details, human_evidence=verified_human_evidence)

    queue_item = build_human_review_queue_item(
        investigation,
        explanation,
        assessment,
        evidence_url=evidence_url or str(docx),
        execution_id=execution_id,
        staged_at=staged_at,
    )
    review_payload = build_review_queue_payload(queue_item)
    operator_result = build_daily_operator_result(
        investigation,
        explanation,
        assessment,
    )

    technical_payload = {
        "investigation": asdict(investigation),
        "case_report": asdict(case_report),
        "human_evidence": verified_human_evidence,
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
    _write_json(operator_json, daily_operator_result_to_dict(operator_result))

    next_action = _next_action(assessment.status)
    summary = {
        "schema_version": SELF_SERVICE_SUMMARY_SCHEMA_VERSION,
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
        "operator_status": operator_result.operator_status,
        "operator_action": operator_result.operator_action,
        "correction_target": operator_result.correction_target,
        "outputs": {
            "case_json": str(technical_json),
            "case_docx": str(docx),
            "registry_update_json": str(registry_json),
            "review_queue_json": str(review_queue_json),
            "daily_operator_result_json": str(operator_json),
        },
        "authority": {
            "human_decision_required": True,
            "automatic_approval_allowed": False,
            "registry_apply_allowed": False,
            "wms_mutation_allowed": False,
            "wme_mutation_allowed": False,
        },
    }
    violations = validate_self_service_summary_contract(summary)
    if violations:
        raise ValueError(
            "self-service summary contract violation: " + ", ".join(violations)
        )
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
        operator_json=str(operator_json),
        summary_json=str(summary_json),
    )


@dataclass(frozen=True, slots=True)
class SelfServiceBatchCaseSpec:
    case_id: str
    product_code: str
    period: str
    report_date: str | None = None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class SelfServiceBatchCaseResult:
    case_id: str
    product_code: str
    status: str
    next_action: str | None = None
    summary_json: str | None = None
    error: str | None = None
    reused: bool = False


@dataclass(frozen=True, slots=True)
class SelfServiceBatchSummary:
    batch_id: str
    total_cases: int
    executed: int
    skipped: int
    eligible: int
    tolerance: int
    hold: int
    error: int
    cases: tuple[SelfServiceBatchCaseResult, ...]
    summary_json: str


def run_self_service_batch(
    *,
    cases: list[SelfServiceBatchCaseSpec],
    sources: InvestigationSources,
    output_dir: str | Path,
    batch_id: str,
    rules_version: str = "0.4",
    engine_commit_sha: str = "LOCAL_OR_UNSET",
) -> SelfServiceBatchSummary:
    """
    Run multiple v0.8 self-service cases with case-level error isolation.

    The batch composes the single-case runner and therefore inherits the same
    authority boundary: no approvals, no registry apply, no WMS/WME mutation.
    """
    batch_clean = str(batch_id).strip()
    if not batch_clean:
        raise ValueError("batch_id este obligatoriu.")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    effective_sources = replace(
        sources,
        cache_dir=sources.cache_dir or (root / ".traceai_cache"),
        use_source_index=sources.use_source_index,
    )

    batch_readiness = validate_source_readiness(
        effective_sources,
        period=None,
    )
    results: list[SelfServiceBatchCaseResult] = []

    for spec in cases:
        if not spec.enabled:
            results.append(
                SelfServiceBatchCaseResult(
                    case_id=spec.case_id,
                    product_code=spec.product_code,
                    status="SKIPPED",
                )
            )
            continue

        case_dir = root / spec.case_id.replace("/", "_")
        reusable_summary = case_dir / "self_service_summary.json"
        reusable_case = case_dir / "case.json"
        if reusable_summary.exists() and reusable_case.exists():
            try:
                summary_payload = json.loads(
                    reusable_summary.read_text(encoding="utf-8")
                )
                technical_payload = json.loads(
                    reusable_case.read_text(encoding="utf-8")
                )
                output_paths = (
                    summary_payload.get("outputs", {})
                    if isinstance(summary_payload.get("outputs"), dict)
                    else {}
                )
                outputs_complete = bool(output_paths) and all(
                    Path(str(path)).exists()
                    for path in output_paths.values()
                    if str(path).strip()
                )
                source_hashes = (
                    technical_payload.get("source_readiness", {})
                    .get("source_hashes", {})
                )
                reusable = (
                    summary_payload.get("case_id") == spec.case_id
                    and summary_payload.get("product_code") == spec.product_code
                    and summary_payload.get("period") == spec.period
                    and summary_payload.get("rules_version") == rules_version
                    and summary_payload.get("engine_commit_sha")
                    == engine_commit_sha
                    and source_hashes == batch_readiness.source_hashes
                    and outputs_complete
                )
                if reusable:
                    results.append(
                        SelfServiceBatchCaseResult(
                            case_id=spec.case_id,
                            product_code=spec.product_code,
                            status=str(
                                summary_payload.get("promotion_status")
                                or "HOLD"
                            ),
                            next_action=summary_payload.get("next_action"),
                            summary_json=str(reusable_summary),
                            reused=True,
                        )
                    )
                    continue
            except (OSError, json.JSONDecodeError, AttributeError, TypeError):
                pass

        try:
            run = run_self_service_case(
                product_code=spec.product_code,
                case_id=spec.case_id,
                period=spec.period,
                report_date=spec.report_date,
                sources=effective_sources,
                output_dir=root,
                rules_version=rules_version,
                engine_commit_sha=engine_commit_sha,
                execution_id=f"{batch_clean}:{spec.case_id}",
            )
            results.append(
                SelfServiceBatchCaseResult(
                    case_id=run.case_id,
                    product_code=run.product_code,
                    status=run.status,
                    next_action=run.next_action,
                    summary_json=run.summary_json,
                )
            )
        except Exception as exc:  # deliberate case-level isolation
            case_dir = root / spec.case_id.replace("/", "_")
            error_path = case_dir / "self_service_error.json"
            _write_json(
                error_path,
                {
                    "schema_version": SELF_SERVICE_SUMMARY_SCHEMA_VERSION,
                    "batch_id": batch_clean,
                    "case_id": spec.case_id,
                    "product_code": spec.product_code,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "authority": {
                        "registry_apply_allowed": False,
                        "wms_mutation_allowed": False,
                        "wme_mutation_allowed": False,
                    },
                },
            )
            results.append(
                SelfServiceBatchCaseResult(
                    case_id=spec.case_id,
                    product_code=spec.product_code,
                    status="ERROR",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    summary_path = root / "self_service_batch_summary.json"
    counts = {
        "total_cases": len(results),
        "executed": sum(
            item.status not in {"SKIPPED", "ERROR"} and not item.reused
            for item in results
        ),
        "skipped": sum(
            item.status == "SKIPPED" or item.reused
            for item in results
        ),
        "eligible": sum(
            item.status == "ELIGIBLE_FOR_HUMAN_REVIEW"
            for item in results
        ),
        "tolerance": sum(
            item.status == "TOLERANCE_MATCH"
            for item in results
        ),
        "hold": sum(item.status == "HOLD" for item in results),
        "error": sum(item.status == "ERROR" for item in results),
    }
    payload = {
        "schema_version": SELF_SERVICE_BATCH_SCHEMA_VERSION,
        "batch_id": batch_clean,
        "engine_version": __version__,
        "rules_version": rules_version,
        "engine_commit_sha": engine_commit_sha,
        **counts,
        "cases": [asdict(item) for item in results],
        "authority": {
            "human_decision_required": True,
            "automatic_approval_allowed": False,
            "registry_apply_allowed": False,
            "wms_mutation_allowed": False,
            "wme_mutation_allowed": False,
        },
    }
    violations = validate_self_service_batch_contract(payload)
    if violations:
        raise ValueError(
            "self-service batch contract violation: " + ", ".join(violations)
        )
    _write_json(summary_path, payload)

    return SelfServiceBatchSummary(
        batch_id=batch_clean,
        cases=tuple(results),
        summary_json=str(summary_path),
        **counts,
    )

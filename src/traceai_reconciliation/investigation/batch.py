from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from traceai_reconciliation import __version__
from traceai_reconciliation.reports import generate_docx_report

from .case_builder import build_case_report
from .engine import investigate_product
from .models import InvestigationSources
from .registry_sync import build_registry_update
from .source_hash_cache import hash_sources


@dataclass(slots=True)
class BatchCaseSpec:
    case_id: str
    product_code: str
    period: str
    report_date: str | None = None
    enabled: bool = True


@dataclass(slots=True)
class BatchCaseResult:
    case_id: str
    product_code: str
    status: str
    verdict: str | None = None
    evidence_level: str | None = None
    initial_difference: float | None = None
    explained_difference: float | None = None
    unexplained_difference: float | None = None
    case_dir: str | None = None
    technical_json: str | None = None
    docx: str | None = None
    registry_json: str | None = None
    error: str | None = None
    elapsed_seconds: float = 0.0
    reused: bool = False


@dataclass(slots=True)
class BatchSummary:
    batch_id: str
    engine_version: str
    rules_version: str
    engine_commit_sha: str
    started_at: str
    finished_at: str
    source_hashes: dict[str, str]
    total_cases: int
    executed: int
    skipped: int
    reused: int
    success: int
    review: int
    error: int
    elapsed_seconds: float
    cases: list[BatchCaseResult] = field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "da", "y"}:
        return True
    if text in {"0", "false", "no", "nu", "n"}:
        return False
    return default


def _case_from_mapping(item: dict[str, Any]) -> BatchCaseSpec:
    required = ["case_id", "product_code", "period"]
    missing = [
        key for key in required
        if not str(item.get(key, "")).strip()
    ]
    if missing:
        raise ValueError(
            "Batch manifest case missing required fields: "
            + ", ".join(missing)
        )

    report_date = str(item.get("report_date", "")).strip() or None
    return BatchCaseSpec(
        case_id=str(item["case_id"]).strip(),
        product_code=str(item["product_code"]).strip(),
        period=str(item["period"]).strip(),
        report_date=report_date,
        enabled=_as_bool(item.get("enabled"), True),
    )


def load_batch_manifest(path: str | Path) -> list[BatchCaseSpec]:
    source = Path(path)
    suffix = source.suffix.lower()

    if suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("cases", [])
        if not isinstance(payload, list):
            raise ValueError(
                "JSON batch manifest must be a list or an object with 'cases'."
            )
        return [
            _case_from_mapping(item)
            for item in payload
            if isinstance(item, dict)
        ]

    if suffix == ".csv":
        with source.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
        return [_case_from_mapping(row) for row in rows]

    raise ValueError(
        "Batch manifest must be .json or .csv."
    )


def _source_paths(
    sources: InvestigationSources,
) -> dict[str, Path]:
    return {
        "stock_report": sources.stock_report,
        "opening_stock_wms": sources.opening_stock_wms,
        "wms_movements": sources.wms_movements,
        "wme_ledger": sources.wme_ledger,
        "production": sources.production,
        "nomenclature": sources.nomenclature,
    }


def _case_signature(
    case: BatchCaseSpec,
    source_hashes: dict[str, str],
    engine_version: str,
    rules_version: str,
    engine_commit_sha: str,
) -> str:
    payload = {
        "case": asdict(case),
        "source_hashes": source_hashes,
        "engine_version": engine_version,
        "rules_version": rules_version,
        "engine_commit_sha": engine_commit_sha,
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_reusable_case(
    technical_json: Path,
    expected_signature: str,
) -> BatchCaseResult | None:
    if not technical_json.exists():
        return None
    try:
        payload = json.loads(
            technical_json.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("batch_signature") != expected_signature:
        return None

    batch_result = payload.get("batch_result")
    if not isinstance(batch_result, dict):
        return None

    required_files = [
        batch_result.get("technical_json"),
        batch_result.get("docx"),
        batch_result.get("registry_json"),
    ]
    if any(
        not value or not Path(value).exists()
        for value in required_files
    ):
        return None

    reused = BatchCaseResult(**batch_result)
    reused.status = "SKIPPED_REUSED"
    reused.reused = True
    reused.elapsed_seconds = 0.0
    return reused


def run_batch(
    cases: list[BatchCaseSpec],
    sources: InvestigationSources,
    output_dir: str | Path,
    *,
    batch_id: str,
    rules_version: str,
    engine_commit_sha: str = "LOCAL_OR_UNSET",
    reuse_completed: bool = True,
) -> BatchSummary:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    if sources.cache_dir is None:
        sources.cache_dir = output_root / ".traceai_cache"
    sources.use_source_index = True

    source_hashes = hash_sources(
        _source_paths(sources),
        cache_dir=sources.cache_dir,
    )

    started_at = _utc_now()
    batch_started = time.perf_counter()
    results: list[BatchCaseResult] = []

    for case in cases:
        case_started = time.perf_counter()
        safe_case_id = case.case_id.replace("/", "_")
        case_dir = output_root / safe_case_id
        technical_path = case_dir / "case.json"
        docx_path = case_dir / "case.docx"
        registry_path = case_dir / "registry_update.json"

        if not case.enabled:
            results.append(
                BatchCaseResult(
                    case_id=case.case_id,
                    product_code=case.product_code,
                    status="SKIPPED",
                    case_dir=str(case_dir),
                    elapsed_seconds=0.0,
                )
            )
            continue

        signature = _case_signature(
            case,
            source_hashes,
            __version__,
            rules_version,
            engine_commit_sha,
        )

        if reuse_completed:
            reused = _load_reusable_case(
                technical_path,
                signature,
            )
            if reused is not None:
                results.append(reused)
                continue

        case_dir.mkdir(parents=True, exist_ok=True)

        try:
            investigation = investigate_product(
                product_code=case.product_code,
                case_id=case.case_id,
                sources=sources,
                period=case.period,
                report_date=case.report_date,
            )
            report = build_case_report(
                investigation,
                engine_version=__version__,
                engine_commit_sha=engine_commit_sha,
                rules_version=rules_version,
                execution_id=(
                    f"{batch_id}:{case.case_id}"
                ),
            )
            registry_update = build_registry_update(
                investigation,
                report,
            )

            generate_docx_report(report, docx_path)
            _write_json(registry_path, registry_update)

            status = (
                "REVIEW"
                if report.verdict == "REVIEW"
                else "SUCCESS"
            )
            elapsed = round(
                time.perf_counter() - case_started,
                3,
            )
            case_result = BatchCaseResult(
                case_id=case.case_id,
                product_code=case.product_code,
                status=status,
                verdict=report.verdict,
                evidence_level=report.evidence_level,
                initial_difference=report.initial_difference,
                explained_difference=report.explained_difference,
                unexplained_difference=report.unexplained_difference,
                case_dir=str(case_dir),
                technical_json=str(technical_path),
                docx=str(docx_path),
                registry_json=str(registry_path),
                elapsed_seconds=elapsed,
            )
            technical_payload = {
                "batch_signature": signature,
                "batch_id": batch_id,
                "investigation": asdict(investigation),
                "case_report": asdict(report),
                "registry_update": registry_update,
                "batch_result": asdict(case_result),
            }
            _write_json(technical_path, technical_payload)

        except Exception as exc:  # deliberate case-level isolation
            elapsed = round(
                time.perf_counter() - case_started,
                3,
            )
            error_path = case_dir / "error.json"
            error_payload = {
                "batch_id": batch_id,
                "case_id": case.case_id,
                "product_code": case.product_code,
                "batch_signature": signature,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            _write_json(error_path, error_payload)
            case_result = BatchCaseResult(
                case_id=case.case_id,
                product_code=case.product_code,
                status="ERROR",
                case_dir=str(case_dir),
                error=f"{type(exc).__name__}: {exc}",
                elapsed_seconds=elapsed,
            )

        results.append(case_result)

    elapsed_seconds = round(
        time.perf_counter() - batch_started,
        3,
    )

    summary = BatchSummary(
        batch_id=batch_id,
        engine_version=__version__,
        rules_version=rules_version,
        engine_commit_sha=engine_commit_sha,
        started_at=started_at,
        finished_at=_utc_now(),
        source_hashes=source_hashes,
        total_cases=len(cases),
        executed=sum(
            1
            for item in results
            if item.status not in {"SKIPPED", "SKIPPED_REUSED"}
        ),
        skipped=sum(
            1 for item in results if item.status == "SKIPPED"
        ),
        reused=sum(
            1 for item in results if item.status == "SKIPPED_REUSED"
        ),
        success=sum(
            1 for item in results if item.status == "SUCCESS"
        ),
        review=sum(
            1 for item in results if item.status == "REVIEW"
        ),
        error=sum(
            1 for item in results if item.status == "ERROR"
        ),
        elapsed_seconds=elapsed_seconds,
        cases=results,
    )

    _write_json(
        output_root / "batch_summary.json",
        asdict(summary),
    )
    return summary

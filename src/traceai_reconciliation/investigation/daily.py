from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from traceai_reconciliation import __version__
from traceai_reconciliation.version import DAILY_RUN_SCHEMA_VERSION, RULESET_VERSION
from traceai_reconciliation.run_store import (
    CaseRecord,
    RunRecord,
    SQLiteRunStore,
    SourceRecord,
)

from .artifact_gate import require_complete_batch_artifacts
from .batch import BatchCaseSpec, load_batch_manifest
from .models import InvestigationSources
from .daily_delta import (
    build_snapshot_state,
    classify_snapshot_delta,
    delta_payload,
    find_previous_run_manifest,
    load_previous_snapshot_state,
)
from .daily_delta_analysis import analyze_daily_delta_root_causes
from .daily_operator_delta import enrich_daily_operator_artifacts
from .daily_operator_history import enrich_operator_history_artifacts
from .daily_case_summary import write_daily_case_summaries
from .self_service import (
    SelfServiceBatchSummary,
    run_self_service_batch,
    validate_source_readiness,
)


@dataclass(frozen=True, slots=True)
class DailyProfile:
    stock_report: str
    opening_stock_wms: str
    wms_movements: str
    wme_ledger: str
    production: str
    nomenclature: str
    manifest: str
    output_dir: str
    period: str
    report_date: str | None = None
    snapshot_at: str | None = None
    opening_absent_means_zero: bool = False
    indexed_cache: bool = True


@dataclass(frozen=True, slots=True)
class DailyRunSummary:
    run_id: str
    status: str
    signature: str | None
    reused_run: bool
    started_at: str
    finished_at: str
    profile_path: str
    manifest_path: str
    output_dir: str
    source_hashes: dict[str, str]
    total_cases: int
    executed: int
    skipped: int
    eligible: int
    tolerance: int
    hold: int
    error: int
    delta_new: int
    delta_changed: int
    delta_unchanged: int
    delta_json: str | None
    delta_root_cause_json: str | None
    previous_run_id: str | None
    batch_summary_json: str | None
    run_manifest_json: str
    summary_json: str
    error_message: str | None = None


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


def _resolve(base: Path, value: str) -> str:
    path = Path(str(value).strip())
    if path.is_absolute():
        return str(path)
    return str((base / path).resolve())


def load_daily_profile(path: str | Path) -> DailyProfile:
    profile_path = Path(path)
    payload = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Daily profile must be a YAML mapping.")

    sources = payload.get("sources") or {}
    daily = payload.get("daily") or {}
    if not isinstance(sources, dict) or not isinstance(daily, dict):
        raise ValueError("Daily profile requires 'sources' and 'daily' mappings.")

    required_sources = (
        "stock_report",
        "opening_stock_wms",
        "wms_movements",
        "wme_ledger",
        "production",
        "nomenclature",
    )
    missing = [
        name for name in required_sources
        if not str(sources.get(name, "")).strip()
    ]
    for name in ("manifest", "output_dir", "period"):
        if not str(daily.get(name, "")).strip():
            missing.append(f"daily.{name}")
    if missing:
        raise ValueError(
            "Daily profile missing required fields: " + ", ".join(missing)
        )

    base = profile_path.parent
    return DailyProfile(
        stock_report=_resolve(base, sources["stock_report"]),
        opening_stock_wms=_resolve(base, sources["opening_stock_wms"]),
        wms_movements=_resolve(base, sources["wms_movements"]),
        wme_ledger=_resolve(base, sources["wme_ledger"]),
        production=_resolve(base, sources["production"]),
        nomenclature=_resolve(base, sources["nomenclature"]),
        manifest=_resolve(base, daily["manifest"]),
        output_dir=_resolve(base, daily["output_dir"]),
        period=str(daily["period"]).strip(),
        report_date=(
            str(daily.get("report_date", "")).strip() or None
        ),
        snapshot_at=(
            str(daily.get("snapshot_at", "")).strip() or None
        ),
        opening_absent_means_zero=bool(
            daily.get("opening_absent_means_zero", False)
        ),
        indexed_cache=bool(daily.get("indexed_cache", True)),
    )


def _sources_from_profile(
    profile: DailyProfile,
    run_root: Path,
) -> InvestigationSources:
    return InvestigationSources(
        stock_report=Path(profile.stock_report),
        opening_stock_wms=Path(profile.opening_stock_wms),
        wms_movements=Path(profile.wms_movements),
        wme_ledger=Path(profile.wme_ledger),
        production=Path(profile.production),
        nomenclature=Path(profile.nomenclature),
        cache_dir=run_root.parent / ".traceai_cache",
        use_source_index=profile.indexed_cache,
        opening_absent_means_zero=profile.opening_absent_means_zero,
    )


def _normalize_cases(
    cases: list[BatchCaseSpec],
    profile: DailyProfile,
) -> list[BatchCaseSpec]:
    normalized: list[BatchCaseSpec] = []
    for item in cases:
        normalized.append(
            BatchCaseSpec(
                case_id=item.case_id,
                product_code=item.product_code,
                period=item.period or profile.period,
                report_date=item.report_date or profile.report_date,
                enabled=item.enabled,
            )
        )
    return normalized


def _signature(
    *,
    profile: DailyProfile,
    cases: list[BatchCaseSpec],
    source_hashes: dict[str, str],
    rules_version: str,
    engine_commit_sha: str,
) -> str:
    payload = {
        "engine_version": __version__,
        "rules_version": rules_version,
        "engine_commit_sha": engine_commit_sha,
        "profile": asdict(profile),
        "cases": [asdict(case) for case in cases],
        "source_hashes": source_hashes,
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_reusable_summary(
    summary_path: Path,
    expected_signature: str,
) -> DailyRunSummary | None:
    if not summary_path.exists():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("signature") != expected_signature:
        return None
    if payload.get("status") == "FAILED_SAFE":
        return None

    batch_summary = payload.get("batch_summary_json")
    manifest_json = payload.get("run_manifest_json")
    if not batch_summary or not Path(batch_summary).exists():
        return None
    if not manifest_json or not Path(manifest_json).exists():
        return None

    payload["reused_run"] = True
    payload["executed"] = 0
    payload["started_at"] = _utc_now()
    payload["finished_at"] = payload["started_at"]
    payload.setdefault("delta_root_cause_json", None)
    return DailyRunSummary(**payload)


def _overall_status(batch: SelfServiceBatchSummary) -> str:
    if batch.error or batch.hold or batch.eligible or batch.tolerance:
        return "SUCCESS_WITH_REVIEW"
    return "SUCCESS"


def run_daily(
    *,
    profile_path: str | Path,
    run_id: str,
    rules_version: str = RULESET_VERSION,
    engine_commit_sha: str = "LOCAL_OR_UNSET",
    reuse_completed: bool = True,
) -> DailyRunSummary:
    clean_run_id = str(run_id).strip()
    if not clean_run_id:
        raise ValueError("run_id este obligatoriu.")

    started_at = _utc_now()
    profile = load_daily_profile(profile_path)
    output_root = Path(profile.output_dir)
    run_root = output_root / clean_run_id.replace("/", "_")
    run_root.mkdir(parents=True, exist_ok=True)

    summary_path = run_root / "daily_run_summary.json"
    run_manifest_path = run_root / "run_manifest.json"
    delta_path = run_root / "daily_delta.json"
    delta_root_cause_path = run_root / "daily_delta_root_cause.json"
    sources = _sources_from_profile(profile, run_root)
    run_store = SQLiteRunStore(output_root / ".traceai_state.sqlite")

    try:
        readiness = validate_source_readiness(
            sources,
            period=profile.period,
        )
        cases = _normalize_cases(
            load_batch_manifest(profile.manifest),
            profile,
        )
        signature = _signature(
            profile=profile,
            cases=cases,
            source_hashes=readiness.source_hashes,
            rules_version=rules_version,
            engine_commit_sha=engine_commit_sha,
        )

        previous_manifest_path = find_previous_run_manifest(
            output_root,
            clean_run_id,
        )

        persisted_previous = run_store.get_latest_successful_run(
            exclude_run_id=clean_run_id,
        )
        previous_run_id = (
            str(persisted_previous.get("run_id") or "").strip()
            if persisted_previous is not None
            else ""
        ) or None
        previous_snapshot_state = (
            run_store.get_snapshot_state(previous_run_id)
            if previous_run_id
            else {}
        )
        previous_source_hashes = (
            run_store.get_source_hashes(previous_run_id)
            if previous_run_id
            else {}
        )
        previous_signature = (
            str(persisted_previous.get("signature") or "").strip() or None
            if persisted_previous is not None
            else None
        )
        previous_snapshot_at = (
            str(persisted_previous.get("snapshot_at") or "").strip() or None
            if persisted_previous is not None
            else None
        )

        previous_batch_summary: str | None = None
        if not previous_run_id or not previous_snapshot_state:
            manifest_run_id, manifest_snapshot_state = (
                load_previous_snapshot_state(previous_manifest_path)
            )
            if not previous_run_id:
                previous_run_id = manifest_run_id
            if not previous_snapshot_state:
                previous_snapshot_state = manifest_snapshot_state

        if previous_manifest_path is not None:
            try:
                previous_manifest_payload = json.loads(
                    previous_manifest_path.read_text(encoding="utf-8")
                )
                if not previous_source_hashes:
                    raw_hashes = (
                        previous_manifest_payload.get("source_readiness", {})
                        .get("source_hashes", {})
                    )
                    if isinstance(raw_hashes, dict):
                        previous_source_hashes = {
                            str(key): str(value)
                            for key, value in raw_hashes.items()
                        }
                if previous_signature is None:
                    previous_signature = str(
                        previous_manifest_payload.get("signature") or ""
                    ) or None
                if previous_snapshot_at is None:
                    previous_profile = previous_manifest_payload.get("profile", {})
                    if isinstance(previous_profile, dict):
                        previous_snapshot_at = (
                            str(previous_profile.get("snapshot_at") or "").strip()
                            or None
                        )
                previous_summary_path = (
                    previous_manifest_path.parent / "daily_run_summary.json"
                )
                if previous_summary_path.exists():
                    previous_summary_payload = json.loads(
                        previous_summary_path.read_text(encoding="utf-8")
                    )
                    previous_batch_summary = (
                        previous_summary_payload.get("batch_summary_json")
                    )
            except (OSError, json.JSONDecodeError, AttributeError):
                previous_batch_summary = None

        snapshot_state = build_snapshot_state(
            profile.stock_report,
            cases,
        )
        source_hashes_changed = (
            not previous_source_hashes
            or previous_source_hashes != readiness.source_hashes
        )
        delta = classify_snapshot_delta(
            current_state=snapshot_state,
            previous_state=previous_snapshot_state,
            source_hashes_changed=source_hashes_changed,
            previous_run_id=previous_run_id,
        )
        _write_json(delta_path, delta_payload(delta))
        delta_root_cause = analyze_daily_delta_root_causes(
            delta=delta,
            current_snapshot_state=snapshot_state,
            previous_snapshot_at=previous_snapshot_at,
            current_snapshot_at=profile.snapshot_at,
            sources=sources,
        )
        _write_json(delta_root_cause_path, asdict(delta_root_cause))

        run_store.begin_run(
            RunRecord(
                run_id=clean_run_id,
                started_at=started_at,
                engine_version=__version__,
                rules_version=rules_version,
                commit_sha=engine_commit_sha,
                signature=signature,
                status="RUNNING",
                snapshot_at=profile.snapshot_at,
                previous_run_id=previous_run_id,
            )
        )
        source_records: list[SourceRecord] = []
        for source_type, source_hash in readiness.source_hashes.items():
            source_path = getattr(sources, source_type, None)
            if source_path is None:
                continue
            source_path = Path(source_path)
            source_records.append(
                SourceRecord(
                    run_id=clean_run_id,
                    source_type=source_type,
                    file_name=source_path.name,
                    size=source_path.stat().st_size,
                    sha256=source_hash,
                )
            )
        run_store.save_sources(source_records)
        delta_root_by_case = {
            item.case_id: item
            for item in delta_root_cause.items
        }
        for item in delta.items:
            root_item = delta_root_by_case.get(item.case_id)
            root_payload = (
                root_item.analysis.get("root_cause", {})
                if root_item is not None
                and isinstance(root_item.analysis, dict)
                else {}
            )
            run_store.save_case(
                CaseRecord(
                    run_id=clean_run_id,
                    case_id=item.case_id,
                    product_code=item.product_code,
                    current_difference=item.current_difference,
                    previous_difference=item.previous_difference,
                    difference_delta=item.difference_delta,
                    execution_policy=item.execution_policy,
                    delta_status=(
                        root_item.status
                        if root_item is not None
                        else None
                    ),
                    explained_delta=(
                        float(root_payload["explained_delta"])
                        if root_payload.get("explained_delta") is not None
                        else None
                    ),
                    residual=(
                        float(root_payload["residual_delta"])
                        if root_payload.get("residual_delta") is not None
                        else None
                    ),
                )
            )

        if reuse_completed:
            reused = _load_reusable_summary(
                summary_path,
                signature,
            )
            if reused is not None:
                _write_json(summary_path, asdict(reused))
                run_store.finish_run(
                    clean_run_id,
                    status=reused.status,
                    finished_at=reused.finished_at,
                    signature=signature,
                )
                return reused

        manifest_payload = {
            "schema_version": DAILY_RUN_SCHEMA_VERSION,
            "run_id": clean_run_id,
            "signature": signature,
            "engine_version": __version__,
            "rules_version": rules_version,
            "engine_commit_sha": engine_commit_sha,
            "profile_path": str(Path(profile_path)),
            "profile": asdict(profile),
            "source_readiness": asdict(readiness),
            "snapshot_state": snapshot_state,
            "delta": delta_payload(delta),
            "delta_root_cause": asdict(delta_root_cause),
            "cases": [asdict(item) for item in cases],
            "authority": {
                "human_decision_required": True,
                "automatic_approval_allowed": False,
                "registry_apply_allowed": False,
                "wms_mutation_allowed": False,
                "wme_mutation_allowed": False,
            },
        }
        _write_json(run_manifest_path, manifest_payload)

        if (
            reuse_completed
            and previous_signature == signature
            and previous_batch_summary
            and Path(previous_batch_summary).exists()
        ):
            summary = DailyRunSummary(
                run_id=clean_run_id,
                status="SUCCESS",
                signature=signature,
                reused_run=True,
                started_at=started_at,
                finished_at=_utc_now(),
                profile_path=str(Path(profile_path)),
                manifest_path=profile.manifest,
                output_dir=str(run_root),
                source_hashes=readiness.source_hashes,
                total_cases=len(cases),
                executed=0,
                skipped=len(cases),
                eligible=0,
                tolerance=0,
                hold=0,
                error=0,
                delta_new=delta.new,
                delta_changed=delta.changed,
                delta_unchanged=delta.unchanged,
                delta_json=str(delta_path),
                delta_root_cause_json=str(delta_root_cause_path),
                previous_run_id=previous_run_id,
                batch_summary_json=previous_batch_summary,
                run_manifest_json=str(run_manifest_path),
                summary_json=str(summary_path),
            )
            _write_json(summary_path, asdict(summary))
            run_store.finish_run(
                clean_run_id,
                status=summary.status,
                finished_at=summary.finished_at,
                signature=signature,
            )
            return summary

        cases_root = run_root / "cases"
        batch = run_self_service_batch(
            cases=cases,
            sources=sources,
            output_dir=cases_root,
            batch_id=f"DAILY:{clean_run_id}",
            rules_version=rules_version,
            engine_commit_sha=engine_commit_sha,
        )
        enrich_daily_operator_artifacts(
            summary=delta_root_cause,
            cases_root=cases_root,
        )
        enrich_operator_history_artifacts(
            run_store=run_store,
            cases=cases,
            cases_root=cases_root,
        )
        write_daily_case_summaries(
            run_id=clean_run_id,
            cases=cases,
            cases_root=cases_root,
        )
        require_complete_batch_artifacts(batch, cases_root)
        summary = DailyRunSummary(
            run_id=clean_run_id,
            status=_overall_status(batch),
            signature=signature,
            reused_run=False,
            started_at=started_at,
            finished_at=_utc_now(),
            profile_path=str(Path(profile_path)),
            manifest_path=profile.manifest,
            output_dir=str(run_root),
            source_hashes=readiness.source_hashes,
            total_cases=batch.total_cases,
            executed=batch.executed,
            skipped=batch.skipped,
            eligible=batch.eligible,
            tolerance=batch.tolerance,
            hold=batch.hold,
            error=batch.error,
            delta_new=delta.new,
            delta_changed=delta.changed,
            delta_unchanged=delta.unchanged,
            delta_json=str(delta_path),
            delta_root_cause_json=str(delta_root_cause_path),
            previous_run_id=previous_run_id,
            batch_summary_json=batch.summary_json,
            run_manifest_json=str(run_manifest_path),
            summary_json=str(summary_path),
        )
        _write_json(summary_path, asdict(summary))
        run_store.finish_run(
            clean_run_id,
            status=summary.status,
            finished_at=summary.finished_at,
            signature=signature,
        )
        return summary

    except Exception as exc:
        failed = DailyRunSummary(
            run_id=clean_run_id,
            status="FAILED_SAFE",
            signature=None,
            reused_run=False,
            started_at=started_at,
            finished_at=_utc_now(),
            profile_path=str(Path(profile_path)),
            manifest_path=profile.manifest,
            output_dir=str(run_root),
            source_hashes={},
            total_cases=0,
            executed=0,
            skipped=0,
            eligible=0,
            tolerance=0,
            hold=0,
            error=1,
            delta_new=0,
            delta_changed=0,
            delta_unchanged=0,
            delta_json=None,
            delta_root_cause_json=None,
            previous_run_id=None,
            batch_summary_json=None,
            run_manifest_json=str(run_manifest_path),
            summary_json=str(summary_path),
            error_message=f"{type(exc).__name__}: {exc}",
        )
        _write_json(
            run_manifest_path,
            {
                "schema_version": DAILY_RUN_SCHEMA_VERSION,
                "run_id": clean_run_id,
                "status": "FAILED_SAFE",
                "error": failed.error_message,
                "authority": {
                    "registry_apply_allowed": False,
                    "wms_mutation_allowed": False,
                    "wme_mutation_allowed": False,
                },
            },
        )
        _write_json(summary_path, asdict(failed))
        try:
            run_store.begin_run(
                RunRecord(
                    run_id=clean_run_id,
                    started_at=started_at,
                    engine_version=__version__,
                    rules_version=rules_version,
                    commit_sha=engine_commit_sha,
                    signature=None,
                    status="FAILED_SAFE",
                    finished_at=failed.finished_at,
                )
            )
        except Exception:
            pass
        return failed

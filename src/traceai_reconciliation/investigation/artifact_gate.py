from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .self_service import SelfServiceBatchSummary
from .case_publication import verify_case_publication


REQUIRED_CASE_ARTIFACTS = (
    "case.json",
    "case.docx",
    "registry_update.json",
    "review_queue.json",
    "self_service_summary.json",
    "daily_operator_result.json",
    "daily_case_summary.json",
)


@dataclass(frozen=True, slots=True)
class ArtifactGateResult:
    complete: bool
    checked_cases: int
    missing: tuple[str, ...]


def validate_batch_artifacts(
    batch: SelfServiceBatchSummary,
    cases_root: str | Path,
    published_case_ids: frozenset[str] = frozenset(),
) -> ArtifactGateResult:
    """Validate that every completed batch case has its required artifacts.

    ERROR cases must preserve their error artifact. SKIPPED cases need no
    artifacts. Any missing required artifact makes the gate fail closed.
    """
    root = Path(cases_root)
    missing: list[str] = []
    checked = 0

    if len(batch.cases) != batch.total_cases:
        missing.append(
            "batch-case-count-mismatch:"
            f"expected={batch.total_cases}:actual={len(batch.cases)}"
        )

    for item in batch.cases:
        case_dir = root / item.case_id.replace("/", "_")
        if item.status == "SKIPPED":
            continue

        checked += 1
        if item.status == "ERROR":
            error_path = case_dir / "self_service_error.json"
            if not error_path.is_file() or error_path.stat().st_size <= 0:
                missing.append(f"{item.case_id}:self_service_error.json")
            continue

        if item.case_id in published_case_ids:
            try:
                verify_case_publication(case_dir, case_id=item.case_id)
            except (ValueError, OSError) as exc:
                missing.append(f"{item.case_id}:invalid-case-publication:{exc}")

        for name in REQUIRED_CASE_ARTIFACTS:
            path = case_dir / name
            if not path.is_file() or path.stat().st_size <= 0:
                missing.append(f"{item.case_id}:{name}")

    return ArtifactGateResult(
        complete=not missing,
        checked_cases=checked,
        missing=tuple(missing),
    )


def require_complete_batch_artifacts(
    batch: SelfServiceBatchSummary,
    cases_root: str | Path,
    published_case_ids: frozenset[str] = frozenset(),
) -> ArtifactGateResult:
    result = validate_batch_artifacts(batch, cases_root, published_case_ids=published_case_ids)
    if not result.complete:
        raise RuntimeError(
            "Artifact completeness gate failed: " + ", ".join(result.missing)
        )
    return result

from pathlib import Path

from traceai_reconciliation.investigation.artifact_gate import (
    REQUIRED_CASE_ARTIFACTS,
    validate_batch_artifacts,
)
from traceai_reconciliation.investigation.self_service import (
    SelfServiceBatchCaseResult,
    SelfServiceBatchSummary,
)


def _batch(status: str = "HOLD") -> SelfServiceBatchSummary:
    return SelfServiceBatchSummary(
        batch_id="BATCH-1",
        total_cases=1,
        executed=1,
        skipped=0,
        eligible=0,
        tolerance=0,
        hold=1 if status == "HOLD" else 0,
        error=1 if status == "ERROR" else 0,
        cases=(
            SelfServiceBatchCaseResult(
                case_id="CASE-1",
                product_code="DS001",
                status=status,
            ),
        ),
        summary_json="batch.json",
    )


def test_artifact_gate_accepts_complete_case(tmp_path: Path) -> None:
    case_dir = tmp_path / "CASE-1"
    case_dir.mkdir()
    for name in REQUIRED_CASE_ARTIFACTS:
        (case_dir / name).write_bytes(b"ok")

    result = validate_batch_artifacts(_batch(), tmp_path)

    assert result.complete is True
    assert result.checked_cases == 1
    assert result.missing == ()


def test_artifact_gate_rejects_missing_operator_output(tmp_path: Path) -> None:
    case_dir = tmp_path / "CASE-1"
    case_dir.mkdir()
    for name in REQUIRED_CASE_ARTIFACTS:
        if name != "daily_operator_result.json":
            (case_dir / name).write_bytes(b"ok")

    result = validate_batch_artifacts(_batch(), tmp_path)

    assert result.complete is False
    assert "CASE-1:daily_operator_result.json" in result.missing


def test_artifact_gate_requires_error_artifact_for_error_case(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "CASE-1"
    case_dir.mkdir()

    result = validate_batch_artifacts(_batch("ERROR"), tmp_path)
    assert result.complete is False

    (case_dir / "self_service_error.json").write_bytes(b"error")
    result = validate_batch_artifacts(_batch("ERROR"), tmp_path)
    assert result.complete is True

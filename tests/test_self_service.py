from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pytest

from traceai_reconciliation.investigation.models import (
    InvestigationSources,
    ProductInvestigationResult,
)
from traceai_reconciliation.investigation.self_service import (
    SelfServiceBatchCaseSpec,
    SelfServiceRunResult,
    run_self_service_batch,
    run_self_service_case,
    validate_source_readiness,
)


def sources(tmp_path: Path) -> InvestigationSources:
    suffixes = {
        "stock_report": ".xlsx",
        "opening_stock_wms": ".xlsx",
        "wms_movements": ".csv",
        "wme_ledger": ".xlsx",
        "production": ".csv",
        "nomenclature": ".xlsx",
    }
    values = {}
    for name, suffix in suffixes.items():
        path = tmp_path / f"{name}{suffix}"
        path.write_text("stub", encoding="utf-8")
        values[name] = path
    return InvestigationSources(**values)


def test_source_readiness_fails_closed_on_missing_source(tmp_path: Path) -> None:
    src = sources(tmp_path)
    src.production.unlink()

    with pytest.raises(FileNotFoundError) as exc:
        validate_source_readiness(src)

    assert "production" in str(exc.value)


def test_self_service_runner_stages_only_and_never_approves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = sources(tmp_path)

    result = ProductInvestigationResult(
        case_id="CASE-SELF-001",
        product_code="TEST",
        product_name="Test",
        unit="KG",
        period="01.01.2026-04.10.2026",
        report_date="08.10.2026",
        initial_difference=-1.0,
        opening_stock_wms=0.0,
        opening_stock_wme=1.0,
        evidence_level="A",
    )

    @dataclass
    class FakeReport:
        verdict: str = "REVIEW"

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.investigate_product",
        lambda **kwargs: result,
    )
    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.build_case_report",
        lambda *args, **kwargs: FakeReport(),
    )
    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.build_registry_update",
        lambda *args, **kwargs: {"operation": "PROPOSE_ONLY"},
    )

    def fake_docx(_report: object, path: str | Path) -> Path:
        output = Path(path)
        output.write_bytes(b"DOCX-STUB")
        return output

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.generate_docx_report",
        fake_docx,
    )

    run = run_self_service_case(
        product_code="TEST",
        case_id="CASE-SELF-001",
        period="01.01.2026-04.10.2026",
        sources=src,
        output_dir=tmp_path / "out",
        staged_at="2026-10-08T18:00:00+00:00",
        execution_id="RUN-V08",
    )

    assert run.status == "ELIGIBLE_FOR_HUMAN_REVIEW"
    assert run.next_action == "HUMAN_REVIEW"

    review = json.loads(Path(run.review_queue_json).read_text(encoding="utf-8"))
    summary = json.loads(Path(run.summary_json).read_text(encoding="utf-8"))

    assert review["operation"] == "STAGE_ONLY"
    assert review["target"]["sheet"] == "VALIDARE_CAZURI"
    assert review["values"]["Review_Status"] == "STAGED"
    assert review["values"]["Decizie_umana"] is None
    assert review["values"]["Registry_Action"] == "NONE"

    assert summary["promotion_status"] == "ELIGIBLE_FOR_HUMAN_REVIEW"
    assert summary["authority"]["automatic_approval_allowed"] is False
    assert summary["authority"]["registry_apply_allowed"] is False
    assert summary["authority"]["wms_mutation_allowed"] is False
    assert summary["authority"]["wme_mutation_allowed"] is False


def test_self_service_hold_remains_hold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = sources(tmp_path)
    result = ProductInvestigationResult(
        case_id="CASE-SELF-HOLD",
        product_code="HOLD",
        product_name="Hold",
        unit="KG",
        period="01.01.2026-04.10.2026",
        report_date="08.10.2026",
        initial_difference=-10.0,
        details={
            "delivery_matching": {
                "residual_total": -10.0,
                "applied_to_explanation": True,
            }
        },
    )

    @dataclass
    class FakeReport:
        verdict: str = "REVIEW"

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.investigate_product",
        lambda **kwargs: result,
    )
    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.build_case_report",
        lambda *args, **kwargs: FakeReport(),
    )
    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.build_registry_update",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.generate_docx_report",
        lambda _report, path: Path(path).write_bytes(b"DOCX-STUB") or Path(path),
    )

    run = run_self_service_case(
        product_code="HOLD",
        case_id="CASE-SELF-HOLD",
        period="01.01.2026-04.10.2026",
        sources=src,
        output_dir=tmp_path / "out",
        staged_at="2026-10-08T18:00:00+00:00",
    )
    summary = json.loads(Path(run.summary_json).read_text(encoding="utf-8"))

    assert run.status == "HOLD"
    assert run.next_action == "RESOLVE_PROMOTION_BLOCKERS"
    assert summary["promotion_status"] == "HOLD"
    assert summary["registry_action"] == "NONE"
    assert summary["blockers"]


def test_source_readiness_rejects_empty_and_invalid_sources(tmp_path: Path) -> None:
    src = sources(tmp_path)
    src.production.write_bytes(b"")

    with pytest.raises(ValueError, match="Empty required sources"):
        validate_source_readiness(
            src,
            period="01.01.2026-04.10.2026",
        )

    src.production.write_text("stub", encoding="utf-8")
    bad = tmp_path / "production.xlsx"
    bad.write_text("stub", encoding="utf-8")
    src.production = bad

    with pytest.raises(ValueError, match="Unsupported source formats"):
        validate_source_readiness(
            src,
            period="01.01.2026-04.10.2026",
        )


def test_source_readiness_captures_hashes_and_period(tmp_path: Path) -> None:
    src = sources(tmp_path)
    src.cache_dir = tmp_path / "cache"

    readiness = validate_source_readiness(
        src,
        period="01.01.2026-04.10.2026",
    )

    assert readiness.ready is True
    assert readiness.period == "01.01.2026-04.10.2026"
    assert set(readiness.source_hashes) == {
        "stock_report",
        "opening_stock_wms",
        "wms_movements",
        "wme_ledger",
        "production",
        "nomenclature",
    }
    assert all(value for value in readiness.source_hashes.values())
    assert all(value > 0 for value in readiness.file_sizes.values())


def test_self_service_batch_isolates_errors_and_preserves_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = sources(tmp_path)

    def fake_run(**kwargs):
        case_id = kwargs["case_id"]
        product_code = kwargs["product_code"]
        root = Path(kwargs["output_dir"]) / case_id
        root.mkdir(parents=True, exist_ok=True)
        summary = root / "self_service_summary.json"
        summary.write_text("{}", encoding="utf-8")

        if product_code == "ERR":
            raise KeyError("produs lipsa")
        status = (
            "ELIGIBLE_FOR_HUMAN_REVIEW"
            if product_code == "OK"
            else "HOLD"
        )
        return SelfServiceRunResult(
            case_id=case_id,
            product_code=product_code,
            status=status,
            next_action=(
                "HUMAN_REVIEW"
                if status == "ELIGIBLE_FOR_HUMAN_REVIEW"
                else "RESOLVE_PROMOTION_BLOCKERS"
            ),
            output_dir=str(root),
            technical_json=str(root / "case.json"),
            docx=str(root / "case.docx"),
            registry_json=str(root / "registry_update.json"),
            review_queue_json=str(root / "review_queue.json"),
            summary_json=str(summary),
        )

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.run_self_service_case",
        fake_run,
    )

    summary = run_self_service_batch(
        cases=[
            SelfServiceBatchCaseSpec(
                case_id="CASE-OK",
                product_code="OK",
                period="01.01.2026-04.10.2026",
            ),
            SelfServiceBatchCaseSpec(
                case_id="CASE-HOLD",
                product_code="HOLD",
                period="01.01.2026-04.10.2026",
            ),
            SelfServiceBatchCaseSpec(
                case_id="CASE-ERR",
                product_code="ERR",
                period="01.01.2026-04.10.2026",
            ),
            SelfServiceBatchCaseSpec(
                case_id="CASE-SKIP",
                product_code="SKIP",
                period="01.01.2026-04.10.2026",
                enabled=False,
            ),
        ],
        sources=src,
        output_dir=tmp_path / "batch",
        batch_id="BATCH-V08",
    )

    assert summary.total_cases == 4
    assert summary.executed == 2
    assert summary.eligible == 1
    assert summary.hold == 1
    assert summary.error == 1
    assert summary.skipped == 1

    payload = json.loads(
        Path(summary.summary_json).read_text(encoding="utf-8")
    )
    assert payload["authority"]["automatic_approval_allowed"] is False
    assert payload["authority"]["registry_apply_allowed"] is False
    assert payload["authority"]["wms_mutation_allowed"] is False
    assert payload["authority"]["wme_mutation_allowed"] is False
    assert any(
        item["case_id"] == "CASE-ERR" and item["status"] == "ERROR"
        for item in payload["cases"]
    )
    assert (
        tmp_path
        / "batch"
        / "CASE-ERR"
        / "self_service_error.json"
    ).exists()


def test_self_service_batch_reuses_completed_case_with_same_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = sources(tmp_path)
    src.cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "batch"
    case_dir = output_dir / "CASE-REUSE"
    case_dir.mkdir(parents=True, exist_ok=True)

    readiness = validate_source_readiness(
        src,
        period="01.01.2026-11.10.2026",
    )
    outputs = {
        "case_json": str(case_dir / "case.json"),
        "case_docx": str(case_dir / "case.docx"),
        "registry_update_json": str(case_dir / "registry_update.json"),
        "review_queue_json": str(case_dir / "review_queue.json"),
    }
    for path in outputs.values():
        Path(path).write_bytes(b"stub")

    (case_dir / "case.json").write_text(
        json.dumps(
            {
                "source_readiness": {
                    "source_hashes": readiness.source_hashes,
                }
            }
        ),
        encoding="utf-8",
    )
    (case_dir / "self_service_summary.json").write_text(
        json.dumps(
            {
                "case_id": "CASE-REUSE",
                "product_code": "REUSE",
                "period": "01.01.2026-11.10.2026",
                "rules_version": "0.9",
                "engine_commit_sha": "abc123",
                "promotion_status": "HOLD",
                "next_action": "RESOLVE_PROMOTION_BLOCKERS",
                "outputs": outputs,
            }
        ),
        encoding="utf-8",
    )

    def forbidden_run(**kwargs):
        raise AssertionError("completed case should have been reused")

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.run_self_service_case",
        forbidden_run,
    )

    summary = run_self_service_batch(
        cases=[
            SelfServiceBatchCaseSpec(
                case_id="CASE-REUSE",
                product_code="REUSE",
                period="01.01.2026-11.10.2026",
            )
        ],
        sources=src,
        output_dir=output_dir,
        batch_id="BATCH-RESUME",
        rules_version="0.9",
        engine_commit_sha="abc123",
    )

    assert summary.total_cases == 1
    assert summary.executed == 0
    assert summary.skipped == 1
    assert summary.hold == 1
    assert summary.error == 0
    assert summary.cases[0].reused is True


def test_self_service_batch_does_not_reuse_after_source_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = sources(tmp_path)
    src.cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "batch"
    case_dir = output_dir / "CASE-REUSE"
    case_dir.mkdir(parents=True, exist_ok=True)

    old_hashes = validate_source_readiness(
        src,
        period="01.01.2026-11.10.2026",
    ).source_hashes
    outputs = {
        "case_json": str(case_dir / "case.json"),
        "case_docx": str(case_dir / "case.docx"),
        "registry_update_json": str(case_dir / "registry_update.json"),
        "review_queue_json": str(case_dir / "review_queue.json"),
    }
    for path in outputs.values():
        Path(path).write_bytes(b"stub")
    (case_dir / "case.json").write_text(
        json.dumps({"source_readiness": {"source_hashes": old_hashes}}),
        encoding="utf-8",
    )
    (case_dir / "self_service_summary.json").write_text(
        json.dumps(
            {
                "case_id": "CASE-REUSE",
                "product_code": "REUSE",
                "period": "01.01.2026-11.10.2026",
                "rules_version": "0.9",
                "engine_commit_sha": "abc123",
                "promotion_status": "HOLD",
                "next_action": "RESOLVE_PROMOTION_BLOCKERS",
                "outputs": outputs,
            }
        ),
        encoding="utf-8",
    )

    src.production.write_text("changed", encoding="utf-8")
    calls = {"count": 0}

    def fake_run(**kwargs):
        calls["count"] += 1
        return SelfServiceRunResult(
            case_id=kwargs["case_id"],
            product_code=kwargs["product_code"],
            status="HOLD",
            next_action="RESOLVE_PROMOTION_BLOCKERS",
            output_dir=str(case_dir),
            technical_json=str(case_dir / "case.json"),
            docx=str(case_dir / "case.docx"),
            registry_json=str(case_dir / "registry_update.json"),
            review_queue_json=str(case_dir / "review_queue.json"),
            summary_json=str(case_dir / "self_service_summary.json"),
        )

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.self_service.run_self_service_case",
        fake_run,
    )

    summary = run_self_service_batch(
        cases=[
            SelfServiceBatchCaseSpec(
                case_id="CASE-REUSE",
                product_code="REUSE",
                period="01.01.2026-11.10.2026",
            )
        ],
        sources=src,
        output_dir=output_dir,
        batch_id="BATCH-RESUME-CHANGED",
        rules_version="0.9",
        engine_commit_sha="abc123",
    )

    assert calls["count"] == 1
    assert summary.executed == 1
    assert summary.skipped == 0
    assert summary.cases[0].reused is False

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
    run_self_service_case,
    validate_source_readiness,
)


def sources(tmp_path: Path) -> InvestigationSources:
    values = {}
    for name in (
        "stock_report",
        "opening_stock_wms",
        "wms_movements",
        "wme_ledger",
        "production",
        "nomenclature",
    ):
        path = tmp_path / f"{name}.dat"
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

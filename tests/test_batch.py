from __future__ import annotations

import json
from pathlib import Path

from traceai_reconciliation.investigation.batch import (
    BatchCaseSpec,
    load_batch_manifest,
    run_batch,
)
from traceai_reconciliation.investigation.models import (
    InvestigationSources,
    ProductInvestigationResult,
)


def _sources(tmp_path: Path) -> InvestigationSources:
    paths = {}
    for name in [
        "stock.xlsx",
        "opening.xlsx",
        "wms.csv",
        "wme.xlsx",
        "production.csv",
        "nomenclature.xlsx",
    ]:
        path = tmp_path / name
        path.write_bytes(f"dummy-{name}".encode())
        paths[name] = path

    return InvestigationSources(
        stock_report=paths["stock.xlsx"],
        opening_stock_wms=paths["opening.xlsx"],
        wms_movements=paths["wms.csv"],
        wme_ledger=paths["wme.xlsx"],
        production=paths["production.csv"],
        nomenclature=paths["nomenclature.xlsx"],
        cache_dir=tmp_path / "cache",
        use_source_index=True,
    )


def _result(
    case_id: str,
    product_code: str,
    *,
    review: bool,
) -> ProductInvestigationResult:
    if review:
        return ProductInvestigationResult(
            case_id=case_id,
            product_code=product_code,
            product_name=f"Produs {product_code}",
            unit="BUC",
            period="01.01.2026-04.10.2026",
            report_date="05.10.2026",
            initial_difference=-10.0,
            reported_stock_wms=0.0,
            reported_stock_wme=10.0,
            verdict="REVIEW",
            evidence_level="B",
            cause_code="CAUSE-MULTI-PARTIAL",
            cause_description="Cauză parțială.",
            cause_status="PROBABILA",
            explained_difference=-8.0,
            unexplained_difference=-2.0,
        )

    return ProductInvestigationResult(
        case_id=case_id,
        product_code=product_code,
        product_name=f"Produs {product_code}",
        unit="BUC",
        period="01.01.2026-04.10.2026",
        report_date="05.10.2026",
        initial_difference=0.0,
        reported_stock_wms=10.0,
        reported_stock_wme=10.0,
        verdict="MATCH_DIRECT",
        evidence_level="A",
        cause_code="CAUSE-NONE",
        cause_description="Fără diferență.",
        cause_status="CONFIRMATA",
        explained_difference=0.0,
        unexplained_difference=0.0,
    )


def test_load_batch_manifest_json_and_csv(tmp_path: Path) -> None:
    json_path = tmp_path / "manifest.json"
    json_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "CASE-1",
                        "product_code": "DS001",
                        "period": "01.01.2026-04.10.2026",
                        "enabled": True,
                    },
                    {
                        "case_id": "CASE-2",
                        "product_code": "DS002",
                        "period": "01.01.2026-04.10.2026",
                        "enabled": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    json_cases = load_batch_manifest(json_path)
    assert len(json_cases) == 2
    assert json_cases[0].enabled is True
    assert json_cases[1].enabled is False

    csv_path = tmp_path / "manifest.csv"
    csv_path.write_text(
        (
            "case_id,product_code,period,enabled\n"
            "CASE-3,DS003,01.01.2026-04.10.2026,da\n"
            "CASE-4,DS004,01.01.2026-04.10.2026,nu\n"
        ),
        encoding="utf-8",
    )
    csv_cases = load_batch_manifest(csv_path)
    assert [item.enabled for item in csv_cases] == [True, False]


def test_batch_isolates_errors_and_counts_statuses(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from traceai_reconciliation.investigation import batch as module

    def fake_investigate_product(
        product_code,
        case_id,
        sources,
        period,
        report_date=None,
    ):
        if product_code == "ERROR":
            raise RuntimeError("synthetic failure")
        return _result(
            case_id,
            product_code,
            review=(product_code == "REVIEW"),
        )

    def fake_generate_docx(report, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"docx")
        return output

    monkeypatch.setattr(
        module,
        "investigate_product",
        fake_investigate_product,
    )
    monkeypatch.setattr(
        module,
        "generate_docx_report",
        fake_generate_docx,
    )

    cases = [
        BatchCaseSpec("CASE-1", "OK", "01.01.2026-04.10.2026"),
        BatchCaseSpec("CASE-2", "REVIEW", "01.01.2026-04.10.2026"),
        BatchCaseSpec("CASE-3", "ERROR", "01.01.2026-04.10.2026"),
        BatchCaseSpec(
            "CASE-4",
            "SKIP",
            "01.01.2026-04.10.2026",
            enabled=False,
        ),
    ]

    summary = run_batch(
        cases,
        _sources(tmp_path),
        tmp_path / "out",
        batch_id="BATCH-TEST",
        rules_version="0.4",
        engine_commit_sha="abc123",
    )

    assert summary.total_cases == 4
    assert summary.executed == 3
    assert summary.skipped == 1
    assert summary.reused == 0
    assert summary.success == 1
    assert summary.review == 1
    assert summary.error == 1

    statuses = {
        item.case_id: item.status
        for item in summary.cases
    }
    assert statuses == {
        "CASE-1": "SUCCESS",
        "CASE-2": "REVIEW",
        "CASE-3": "ERROR",
        "CASE-4": "SKIPPED",
    }

    assert (
        tmp_path / "out" / "CASE-1" / "case.json"
    ).exists()
    assert (
        tmp_path / "out" / "CASE-2" / "registry_update.json"
    ).exists()
    assert (
        tmp_path / "out" / "CASE-3" / "error.json"
    ).exists()
    assert (tmp_path / "out" / "batch_summary.json").exists()


def test_batch_reuses_complete_case_with_same_signature(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from traceai_reconciliation.investigation import batch as module

    calls = {"count": 0}

    def fake_investigate_product(
        product_code,
        case_id,
        sources,
        period,
        report_date=None,
    ):
        calls["count"] += 1
        return _result(case_id, product_code, review=True)

    def fake_generate_docx(report, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"docx")
        return output

    monkeypatch.setattr(
        module,
        "investigate_product",
        fake_investigate_product,
    )
    monkeypatch.setattr(
        module,
        "generate_docx_report",
        fake_generate_docx,
    )

    cases = [
        BatchCaseSpec(
            "CASE-1",
            "DS001",
            "01.01.2026-04.10.2026",
        )
    ]
    sources = _sources(tmp_path)
    output = tmp_path / "out"

    first = run_batch(
        cases,
        sources,
        output,
        batch_id="BATCH-TEST",
        rules_version="0.4",
        engine_commit_sha="abc123",
    )
    second = run_batch(
        cases,
        sources,
        output,
        batch_id="BATCH-TEST",
        rules_version="0.4",
        engine_commit_sha="abc123",
    )

    assert calls["count"] == 1
    assert first.review == 1
    assert second.executed == 0
    assert second.reused == 1
    assert second.cases[0].status == "SKIPPED_REUSED"
    assert second.cases[0].reused is True


def test_batch_signature_invalidates_when_rules_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from traceai_reconciliation.investigation import batch as module

    calls = {"count": 0}

    def fake_investigate_product(
        product_code,
        case_id,
        sources,
        period,
        report_date=None,
    ):
        calls["count"] += 1
        return _result(case_id, product_code, review=True)

    def fake_generate_docx(report, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"docx")
        return output

    monkeypatch.setattr(
        module,
        "investigate_product",
        fake_investigate_product,
    )
    monkeypatch.setattr(
        module,
        "generate_docx_report",
        fake_generate_docx,
    )

    cases = [
        BatchCaseSpec(
            "CASE-1",
            "DS001",
            "01.01.2026-04.10.2026",
        )
    ]
    sources = _sources(tmp_path)
    output = tmp_path / "out"

    run_batch(
        cases,
        sources,
        output,
        batch_id="BATCH-TEST",
        rules_version="0.4",
        engine_commit_sha="abc123",
    )
    second = run_batch(
        cases,
        sources,
        output,
        batch_id="BATCH-TEST",
        rules_version="0.5",
        engine_commit_sha="abc123",
    )

    assert calls["count"] == 2
    assert second.reused == 0
    assert second.executed == 1

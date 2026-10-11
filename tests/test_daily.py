from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from traceai_reconciliation.investigation.daily import (
    load_daily_profile,
    run_daily,
)
from traceai_reconciliation.investigation.self_service import (
    SelfServiceBatchSummary,
)


def _write_sources(root: Path) -> None:
    files = {
        "stock.xlsx": b"stock",
        "opening.xlsx": b"opening",
        "wms.csv": b"wms",
        "wme.xlsx": b"wme",
        "production.csv": b"production",
        "nomenclature.xlsx": b"nomenclature",
    }
    for name, content in files.items():
        (root / name).write_bytes(content)


def _write_profile(root: Path) -> Path:
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "CASE-DAILY-001",
                        "product_code": "DS001",
                        "period": "01.01.2026-04.10.2026",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    profile = root / "daily.yaml"
    profile.write_text(
        """
sources:
  stock_report: stock.xlsx
  opening_stock_wms: opening.xlsx
  wms_movements: wms.csv
  wme_ledger: wme.xlsx
  production: production.csv
  nomenclature: nomenclature.xlsx

daily:
  manifest: manifest.json
  output_dir: daily_runs
  period: 01.01.2026-04.10.2026
  report_date: 11.10.2026
  opening_absent_means_zero: true
  indexed_cache: true
""".strip(),
        encoding="utf-8",
    )
    return profile


def test_load_daily_profile_resolves_paths(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    profile_path = _write_profile(tmp_path)

    profile = load_daily_profile(profile_path)

    assert Path(profile.stock_report) == (tmp_path / "stock.xlsx").resolve()
    assert Path(profile.manifest) == (tmp_path / "manifest.json").resolve()
    assert Path(profile.output_dir) == (tmp_path / "daily_runs").resolve()
    assert profile.opening_absent_means_zero is True
    assert profile.indexed_cache is True


def test_daily_run_writes_manifest_and_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_sources(tmp_path)
    profile_path = _write_profile(tmp_path)

    def fake_batch(**kwargs):
        root = Path(kwargs["output_dir"])
        root.mkdir(parents=True, exist_ok=True)
        summary_json = root / "self_service_batch_summary.json"
        summary_json.write_text("{}", encoding="utf-8")
        return SelfServiceBatchSummary(
            batch_id=kwargs["batch_id"],
            total_cases=1,
            executed=1,
            skipped=0,
            eligible=1,
            tolerance=0,
            hold=0,
            error=0,
            cases=(),
            summary_json=str(summary_json),
        )

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.daily.run_self_service_batch",
        fake_batch,
    )

    result = run_daily(
        profile_path=profile_path,
        run_id="2026-10-11",
        rules_version="0.9-dev",
        engine_commit_sha="abc123",
    )

    assert result.status == "SUCCESS_WITH_REVIEW"
    assert result.reused_run is False
    assert result.total_cases == 1
    assert result.eligible == 1
    assert Path(result.run_manifest_json).exists()
    assert Path(result.summary_json).exists()

    manifest = json.loads(
        Path(result.run_manifest_json).read_text(encoding="utf-8")
    )
    assert manifest["authority"]["registry_apply_allowed"] is False
    assert manifest["authority"]["wms_mutation_allowed"] is False
    assert manifest["source_readiness"]["ready"] is True


def test_daily_run_is_idempotent_for_same_signature(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_sources(tmp_path)
    profile_path = _write_profile(tmp_path)
    calls = {"count": 0}

    def fake_batch(**kwargs):
        calls["count"] += 1
        root = Path(kwargs["output_dir"])
        root.mkdir(parents=True, exist_ok=True)
        summary_json = root / "self_service_batch_summary.json"
        summary_json.write_text("{}", encoding="utf-8")
        return SelfServiceBatchSummary(
            batch_id=kwargs["batch_id"],
            total_cases=1,
            executed=1,
            skipped=0,
            eligible=0,
            tolerance=0,
            hold=0,
            error=0,
            cases=(),
            summary_json=str(summary_json),
        )

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.daily.run_self_service_batch",
        fake_batch,
    )

    first = run_daily(
        profile_path=profile_path,
        run_id="2026-10-11",
        rules_version="0.9-dev",
        engine_commit_sha="abc123",
    )
    second = run_daily(
        profile_path=profile_path,
        run_id="2026-10-11",
        rules_version="0.9-dev",
        engine_commit_sha="abc123",
    )

    assert calls["count"] == 1
    assert first.status == "SUCCESS"
    assert second.status == "SUCCESS"
    assert second.reused_run is True
    assert second.executed == 0
    assert first.signature == second.signature


def test_daily_run_fails_closed_before_batch_on_missing_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_sources(tmp_path)
    profile_path = _write_profile(tmp_path)
    (tmp_path / "production.csv").unlink()
    calls = {"count": 0}

    def fake_batch(**kwargs):
        calls["count"] += 1
        raise AssertionError("batch must not run when source readiness fails")

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.daily.run_self_service_batch",
        fake_batch,
    )

    result = run_daily(
        profile_path=profile_path,
        run_id="2026-10-11-missing",
    )

    assert calls["count"] == 0
    assert result.status == "FAILED_SAFE"
    assert result.error == 1
    assert "production" in (result.error_message or "")
    assert Path(result.summary_json).exists()

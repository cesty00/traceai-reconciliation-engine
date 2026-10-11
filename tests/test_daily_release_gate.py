from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from traceai_reconciliation.investigation.daily import run_daily
from traceai_reconciliation.investigation.self_service import SelfServiceBatchSummary


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fixture(root: Path) -> Path:
    pd.DataFrame(
        [
            {
                "CodArticol": "DS-GATE-001",
                "DenumireArticol": "Produs release gate",
                "QuantityERP": 11.0,
                "QuantityWMS": 10.0,
                "QuantityDifference": -1.0,
            }
        ]
    ).to_excel(root / "stock.xlsx", index=False)

    for name, content in {
        "opening.xlsx": b"opening",
        "wms.csv": b"wms",
        "wme.xlsx": b"wme",
        "production.csv": b"production",
        "nomenclature.xlsx": b"nomenclature",
    }.items():
        (root / name).write_bytes(content)

    (root / "manifest.json").write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "CASE-RELEASE-GATE-001",
                        "product_code": "DS-GATE-001",
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


def _fake_batch(**kwargs) -> SelfServiceBatchSummary:
    root = Path(kwargs["output_dir"])
    root.mkdir(parents=True, exist_ok=True)
    summary_json = root / "self_service_batch_summary.json"
    summary_json.write_text(
        json.dumps(
            {
                "authority": {
                    "human_decision_required": True,
                    "automatic_approval_allowed": False,
                    "registry_apply_allowed": False,
                    "wms_mutation_allowed": False,
                    "wme_mutation_allowed": False,
                }
            }
        ),
        encoding="utf-8",
    )
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


def test_daily_release_gate_enforces_read_only_authority(
    tmp_path: Path,
    monkeypatch,
) -> None:
    profile = _write_fixture(tmp_path)
    monkeypatch.setattr(
        "traceai_reconciliation.investigation.daily.run_self_service_batch",
        _fake_batch,
    )

    result = run_daily(
        profile_path=profile,
        run_id="release-gate",
        rules_version="0.9-dev",
        engine_commit_sha="release-gate",
    )

    assert result.status == "SUCCESS_WITH_REVIEW"
    manifest = json.loads(
        Path(result.run_manifest_json).read_text(encoding="utf-8")
    )
    authority = manifest["authority"]
    assert authority["human_decision_required"] is True
    assert authority["automatic_approval_allowed"] is False
    assert authority["registry_apply_allowed"] is False
    assert authority["wms_mutation_allowed"] is False
    assert authority["wme_mutation_allowed"] is False


def test_daily_release_gate_does_not_mutate_input_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    profile = _write_fixture(tmp_path)
    monkeypatch.setattr(
        "traceai_reconciliation.investigation.daily.run_self_service_batch",
        _fake_batch,
    )
    inputs = [
        tmp_path / "stock.xlsx",
        tmp_path / "opening.xlsx",
        tmp_path / "wms.csv",
        tmp_path / "wme.xlsx",
        tmp_path / "production.csv",
        tmp_path / "nomenclature.xlsx",
        tmp_path / "manifest.json",
    ]
    before = {path.name: _sha(path) for path in inputs}

    run_daily(
        profile_path=profile,
        run_id="release-gate-immutability",
        rules_version="0.9-dev",
        engine_commit_sha="release-gate",
    )

    after = {path.name: _sha(path) for path in inputs}
    assert after == before


def test_daily_release_gate_missing_source_is_failed_safe(
    tmp_path: Path,
    monkeypatch,
) -> None:
    profile = _write_fixture(tmp_path)
    (tmp_path / "production.csv").unlink()

    def forbidden_batch(**kwargs):
        raise AssertionError("daily batch must not run after source readiness failure")

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.daily.run_self_service_batch",
        forbidden_batch,
    )

    result = run_daily(
        profile_path=profile,
        run_id="release-gate-failed-safe",
        rules_version="0.9-dev",
        engine_commit_sha="release-gate",
    )

    assert result.status == "FAILED_SAFE"
    manifest = json.loads(
        Path(result.run_manifest_json).read_text(encoding="utf-8")
    )
    assert manifest["authority"]["registry_apply_allowed"] is False
    assert manifest["authority"]["wms_mutation_allowed"] is False
    assert manifest["authority"]["wme_mutation_allowed"] is False

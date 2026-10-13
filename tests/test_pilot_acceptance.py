from __future__ import annotations

import json
from pathlib import Path

from traceai_reconciliation import __version__
from traceai_reconciliation.pilot_acceptance import evaluate_pilot_run
from traceai_reconciliation.run_store import (
    RunRecord,
    SQLiteRunStore,
    SourceRecord,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_valid_pilot(root: Path) -> Path:
    output_dir = root / "daily_runs" / "PILOT-1"
    cases_root = output_dir / "cases"
    case_dir = cases_root / "CASE-1"
    case_dir.mkdir(parents=True, exist_ok=True)

    case_summary = {
        "schema_version": "1.0",
        "run_id": "PILOT-1",
        "case_id": "CASE-1",
        "product_code": "DS001",
        "product_name": "Produs",
        "unit": "KG",
        "difference": 1.0,
        "cause": "NECLAR",
        "cause_status": "REVIEW",
        "evidence_level": "C",
        "correction_target": "REVIEW",
        "operator_status": "REVIEW",
        "operator_action": "Verificare umană",
        "residual": 1.0,
        "daily_delta": {"status": "UNEXPLAINED"},
        "history": {
            "history_status": "NEW_HISTORY",
            "runs_available": 1,
            "recent_runs": [],
        },
        "evidence": [],
        "blockers": [],
        "warnings": [],
        "authority": {
            "human_decision_required": True,
            "automatic_approval_allowed": False,
            "registry_apply_allowed": False,
            "wms_mutation_allowed": False,
            "wme_mutation_allowed": False,
        },
    }
    _write_json(case_dir / "daily_case_summary.json", case_summary)

    manifest = {
        "run_id": "PILOT-1",
        "profile": {
            "snapshot_at": "2026-10-13T18:00:00+00:00",
        },
        "cases": [
            {
                "case_id": "CASE-1",
                "product_code": "DS001",
                "enabled": True,
            }
        ],
        "authority": {
            "human_decision_required": True,
            "automatic_approval_allowed": False,
            "registry_apply_allowed": False,
            "wms_mutation_allowed": False,
            "wme_mutation_allowed": False,
        },
    }
    manifest_path = output_dir / "daily_run_manifest.json"
    _write_json(manifest_path, manifest)

    source_hashes = {
        "stock_report": "a",
        "opening_stock_wms": "b",
        "wms_movements": "c",
        "wme_ledger": "d",
        "production": "e",
        "nomenclature": "f",
    }
    summary = {
        "run_id": "PILOT-1",
        "status": "SUCCESS_WITH_REVIEW",
        "signature": "sig-1",
        "error": 0,
        "source_hashes": source_hashes,
        "run_manifest_json": str(manifest_path),
        "output_dir": str(output_dir),
    }
    summary_path = output_dir / "daily_run_summary.json"
    _write_json(summary_path, summary)

    store = SQLiteRunStore(output_dir.parent / ".traceai_state.sqlite")
    store.begin_run(
        RunRecord(
            run_id="PILOT-1",
            started_at="2026-10-13T18:01:00+00:00",
            engine_version=__version__,
            rules_version="0.4",
            commit_sha="abc123",
            signature="sig-1",
            status="SUCCESS_WITH_REVIEW",
            snapshot_at="2026-10-13T18:00:00+00:00",
        )
    )
    store.save_sources(
        [
            SourceRecord(
                run_id="PILOT-1",
                source_type=source_type,
                file_name=f"{source_type}.dat",
                size=1,
                sha256=sha,
            )
            for source_type, sha in source_hashes.items()
        ]
    )
    return summary_path


def test_valid_completed_daily_run_is_pilot_accepted(tmp_path: Path) -> None:
    summary_path = _write_valid_pilot(tmp_path)

    result = evaluate_pilot_run(summary_path)

    assert result.accepted is True
    assert result.run_id == "PILOT-1"
    assert result.engine_version == __version__
    assert result.checked_cases == 1
    assert result.blockers == ()


def test_pilot_rejects_missing_snapshot_and_authority_violation(
    tmp_path: Path,
) -> None:
    summary_path = _write_valid_pilot(tmp_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest_path = Path(summary["run_manifest_json"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["profile"]["snapshot_at"] = None
    manifest["authority"]["wms_mutation_allowed"] = True
    _write_json(manifest_path, manifest)

    result = evaluate_pilot_run(summary_path)

    assert result.accepted is False
    assert "missing:snapshot_at" in result.blockers
    assert "authority:wms_mutation_allowed" in result.blockers


def test_pilot_rejects_missing_required_case_summary(tmp_path: Path) -> None:
    summary_path = _write_valid_pilot(tmp_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    case_summary = (
        Path(summary["output_dir"])
        / "cases"
        / "CASE-1"
        / "daily_case_summary.json"
    )
    case_summary.unlink()

    result = evaluate_pilot_run(summary_path)

    assert result.accepted is False
    assert "CASE-1:missing:daily_case_summary.json" in result.blockers


def test_pilot_rejects_failed_safe_run(tmp_path: Path) -> None:
    summary_path = _write_valid_pilot(tmp_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["status"] = "FAILED_SAFE"
    summary["error"] = 1
    _write_json(summary_path, summary)

    result = evaluate_pilot_run(summary_path)

    assert result.accepted is False
    assert "run_status:FAILED_SAFE" in result.blockers
    assert "run_errors:1" in result.blockers


def test_pilot_rejects_current_history_still_marked_running(
    tmp_path: Path,
) -> None:
    summary_path = _write_valid_pilot(tmp_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    case_path = (
        Path(summary["output_dir"])
        / "cases"
        / "CASE-1"
        / "daily_case_summary.json"
    )
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["history"]["recent_runs"] = [
        {
            "run_id": "PILOT-1",
            "run_status": "RUNNING",
        }
    ]
    _write_json(case_path, payload)

    result = evaluate_pilot_run(summary_path)

    assert result.accepted is False
    assert (
        "CASE-1:history:current_run_status=RUNNING"
        in result.blockers
    )

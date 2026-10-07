from __future__ import annotations

import json
from pathlib import Path

from traceai_reconciliation.investigation.registry_apply_plan import (
    build_registry_apply_plan,
    write_registry_apply_plan,
)


def _write_case_payload(
    root: Path,
    case_id: str,
    *,
    product: str = "DS001",
    period: str = "01.01.2026-04.10.2026",
    difference: float = -10.0,
    evidence: str = "B",
    status: str = "IN_ANALIZA",
) -> Path:
    case_dir = root / case_id
    case_dir.mkdir(parents=True)
    payload = {
        "values": {
            "CASE_ID": case_id,
            "Perioada_WMS": period,
            "Cod_produs": product,
            "Diferenta": difference,
            "Verdict": "REVIEW",
            "Nivel_proba": evidence,
            "Cauza": "CAUSE-TEST",
            "Regula_aplicata": "DEL-02",
            "Status_investigatie": status,
            "Observatii": "Test.",
        },
        "preserve_if_empty": [
            "Data_deschidere",
            "Link_dovezi_Drive",
        ],
    }
    path = case_dir / "registry_update.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return case_dir


def _write_summary(
    root: Path,
    cases: list[dict],
) -> Path:
    path = root / "batch_summary.json"
    path.write_text(
        json.dumps(
            {
                "batch_id": "BATCH-1",
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_registry_apply_plan_marks_safe_existing_update(
    tmp_path: Path,
) -> None:
    case_dir = _write_case_payload(
        tmp_path,
        "CASE-1",
    )
    summary = _write_summary(
        tmp_path,
        [
            {
                "case_id": "CASE-1",
                "product_code": "DS001",
                "status": "REVIEW",
                "case_dir": str(case_dir),
            }
        ],
    )
    registry = [
        {
            "CASE_ID": "CASE-1",
            "Perioada_WMS": "01.01.2026–04.10.2026",
            "Cod_produs": "DS001",
            "Diferenta": "-10",
            "Status_investigatie": "DESCHIS",
        }
    ]

    plan = build_registry_apply_plan(registry, summary)

    assert plan["counts"] == {"SAFE_UPDATE_EXISTING": 1}
    item = plan["items"][0]
    assert item["action"] == "SAFE_UPDATE_EXISTING"
    assert item["proposed"]["Nivel_proba"] == "B"
    assert "Data_deschidere" in item["preserve_if_empty"]


def test_registry_apply_plan_holds_difference_mismatch(
    tmp_path: Path,
) -> None:
    case_dir = _write_case_payload(
        tmp_path,
        "CASE-1",
        difference=-10.0,
    )
    summary = _write_summary(
        tmp_path,
        [
            {
                "case_id": "CASE-1",
                "product_code": "DS001",
                "status": "REVIEW",
                "case_dir": str(case_dir),
            }
        ],
    )
    registry = [
        {
            "CASE_ID": "CASE-1",
            "Perioada_WMS": "01.01.2026-04.10.2026",
            "Cod_produs": "DS001",
            "Diferenta": "-11",
        }
    ]

    plan = build_registry_apply_plan(registry, summary)
    assert plan["items"][0]["action"] == "HOLD_DIFFERENCE_MISMATCH"


def test_registry_apply_plan_holds_low_evidence(
    tmp_path: Path,
) -> None:
    case_dir = _write_case_payload(
        tmp_path,
        "CASE-1",
        evidence="C",
    )
    summary = _write_summary(
        tmp_path,
        [
            {
                "case_id": "CASE-1",
                "product_code": "DS001",
                "status": "REVIEW",
                "case_dir": str(case_dir),
            }
        ],
    )
    registry = [
        {
            "CASE_ID": "CASE-1",
            "Perioada_WMS": "01.01.2026-04.10.2026",
            "Cod_produs": "DS001",
            "Diferenta": "-10",
        }
    ]

    plan = build_registry_apply_plan(
        registry,
        summary,
        minimum_evidence="B",
    )
    assert plan["items"][0]["action"] == "HOLD_EVIDENCE"


def test_registry_apply_plan_holds_error_without_payload(
    tmp_path: Path,
) -> None:
    summary = _write_summary(
        tmp_path,
        [
            {
                "case_id": "CASE-ERR",
                "product_code": "BAD",
                "status": "ERROR",
                "error": "synthetic failure",
            }
        ],
    )

    plan = build_registry_apply_plan([], summary)

    assert plan["counts"] == {"HOLD_ERROR": 1}
    assert plan["items"][0]["reason"] == "synthetic failure"


def test_registry_apply_plan_holds_missing_case(
    tmp_path: Path,
) -> None:
    case_dir = _write_case_payload(
        tmp_path,
        "CASE-MISSING",
    )
    summary = _write_summary(
        tmp_path,
        [
            {
                "case_id": "CASE-MISSING",
                "product_code": "DS001",
                "status": "REVIEW",
                "case_dir": str(case_dir),
            }
        ],
    )

    plan = build_registry_apply_plan([], summary)

    assert plan["items"][0]["action"] == "HOLD_MISSING_CASE"


def test_write_registry_apply_plan(tmp_path: Path) -> None:
    plan = {
        "schema_version": "1.0",
        "batch_id": "BATCH-1",
        "counts": {"SAFE_UPDATE_EXISTING": 1},
        "items": [],
    }
    output = write_registry_apply_plan(
        tmp_path / "plan.json",
        plan,
    )
    assert output.exists()
    assert json.loads(output.read_text())["batch_id"] == "BATCH-1"

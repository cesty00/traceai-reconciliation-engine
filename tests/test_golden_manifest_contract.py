from __future__ import annotations

import json
from pathlib import Path

from traceai_reconciliation.investigation.golden_gate import GoldenExpectation


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "golden_cases_expectations_v0.3.json"
)


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_official_golden_manifest_has_17_cases() -> None:
    payload = _payload()
    assert payload["source_manifest_version"] == "0.3"
    assert payload["case_count"] == 17
    assert len(payload["cases"]) == 17


def test_official_golden_cases_are_unique_evidence_a_exact_and_residual_zero() -> None:
    cases = _payload()["cases"]
    case_ids = [item["case_id"] for item in cases]
    products = [item["product_code"] for item in cases]

    assert len(case_ids) == len(set(case_ids))
    assert len(products) == len(set(products))
    assert all(item["evidence"] == "A" for item in cases)
    assert all(item["expected_status"] == "EXACT" for item in cases)
    assert all(abs(float(item["residual"])) <= 1e-12 for item in cases)


def test_official_golden_cases_load_into_gate_contract() -> None:
    for item in _payload()["cases"]:
        expectation = GoldenExpectation(
            case_id=item["case_id"],
            product_code=item["product_code"],
            difference=float(item["difference"]),
            explained=float(item["explained"]),
            residual=float(item["residual"]),
            rules=tuple(item["contributing_rules"]),
            supporting_rules=tuple(item["supporting_rules"]),
            expected_status=item["expected_status"],
        )
        assert expectation.case_id
        assert expectation.product_code
        assert abs(expectation.difference - expectation.explained) <= 1e-12
        assert expectation.residual == 0.0

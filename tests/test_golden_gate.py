from __future__ import annotations

from traceai_reconciliation.investigation.auto_explain import (
    ExplanationComponent,
    compose_explanation,
)
from traceai_reconciliation.investigation.golden_gate import (
    GoldenExpectation,
    compare_auto_explanation,
    summarize_golden_gate,
)


def comp(cid: str, rule: str, effect: float) -> ExplanationComponent:
    return ExplanationComponent(
        component_id=cid,
        rule_id=rule,
        effect=effect,
        description=cid,
    )


def test_golden_gate_passes_exact_expected_equation() -> None:
    explanation = compose_explanation(
        -70.0,
        [
            comp("opening", "OPEN-01", -1.0),
            comp("production", "PROD-02", -202.0),
            comp("pv", "GST-04", 140.0),
            comp("delivery", "DEL-02", -7.0),
        ],
    )
    expectation = GoldenExpectation(
        case_id="CASE-GOLDEN-001",
        product_code="TEST",
        difference=-70.0,
        explained=-70.0,
        residual=0.0,
        rules=("OPEN-01", "PROD-02", "GST-04", "DEL-02"),
    )

    result = compare_auto_explanation(expectation, explanation)

    assert result.passed is True
    assert result.mismatches == ()


def test_golden_gate_reports_numeric_and_rule_regression() -> None:
    explanation = compose_explanation(
        -70.0,
        [
            comp("opening", "OPEN-01", -1.0),
            comp("production", "PROD-02", -60.0),
        ],
    )
    expectation = GoldenExpectation(
        case_id="CASE-GOLDEN-002",
        product_code="TEST",
        difference=-70.0,
        explained=-70.0,
        residual=0.0,
        rules=("OPEN-01", "PROD-02", "DEL-02"),
    )

    result = compare_auto_explanation(expectation, explanation)

    assert result.passed is False
    assert any("explained_difference" in item for item in result.mismatches)
    assert any("residual_difference" in item for item in result.mismatches)
    assert any("status" in item for item in result.mismatches)
    assert any("rules" in item for item in result.mismatches)


def test_golden_gate_tolerance_is_numeric() -> None:
    explanation = compose_explanation(
        -4.0004,
        [comp("opening", "OPEN-01", -4.0004)],
        decimals=4,
    )
    expectation = GoldenExpectation(
        case_id="CASE-GOLDEN-003",
        product_code="TEST",
        difference=-4.0,
        explained=-4.0,
        residual=0.0,
        rules=("OPEN-01",),
    )

    result = compare_auto_explanation(
        expectation,
        explanation,
        tolerance=0.001,
    )

    assert result.passed is True


def test_golden_gate_summary_fails_if_one_case_regresses() -> None:
    good = compare_auto_explanation(
        GoldenExpectation(
            case_id="GOOD",
            product_code="A",
            difference=-1.0,
            explained=-1.0,
            residual=0.0,
            rules=("OPEN-01",),
        ),
        compose_explanation(-1.0, [comp("a", "OPEN-01", -1.0)]),
    )
    bad = compare_auto_explanation(
        GoldenExpectation(
            case_id="BAD",
            product_code="B",
            difference=-2.0,
            explained=-2.0,
            residual=0.0,
            rules=("OPEN-01",),
        ),
        compose_explanation(-2.0, [comp("b", "OPEN-01", -1.0)]),
    )

    summary = summarize_golden_gate([good, bad])

    assert summary["status"] == "FAIL"
    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["failed_cases"][0]["case_id"] == "BAD"

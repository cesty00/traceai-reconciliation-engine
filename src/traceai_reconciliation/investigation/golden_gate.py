from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .auto_explain import AutoExplanation


@dataclass(frozen=True, slots=True)
class GoldenExpectation:
    case_id: str
    product_code: str
    difference: float
    explained: float
    residual: float
    rules: tuple[str, ...] = ()
    supporting_rules: tuple[str, ...] = ()
    expected_status: str = "EXACT"


@dataclass(frozen=True, slots=True)
class GoldenGateResult:
    case_id: str
    product_code: str
    passed: bool
    mismatches: tuple[str, ...]


def compare_auto_explanation(
    expectation: GoldenExpectation,
    explanation: AutoExplanation,
    *,
    tolerance: float = 0.001,
    compare_rules: bool = True,
) -> GoldenGateResult:
    """
    Compare one Auto Explain result with a curated Golden Case expectation.

    Only numeric/contributing rules are compared. supporting_rules are audit
    context and MUST NOT create extra explanation components or double count
    the equation.

    The gate is read-only. It never mutates the investigation, registry or
    source data.
    """
    mismatches: list[str] = []

    def numeric(label: str, actual: float, expected: float) -> None:
        if abs(float(actual) - float(expected)) > tolerance:
            mismatches.append(
                f"{label}: actual={actual:.6f}, expected={expected:.6f}"
            )

    numeric(
        "initial_difference",
        explanation.initial_difference,
        expectation.difference,
    )
    numeric(
        "explained_difference",
        explanation.explained_difference,
        expectation.explained,
    )
    numeric(
        "residual_difference",
        explanation.residual_difference,
        expectation.residual,
    )

    if explanation.status != expectation.expected_status:
        mismatches.append(
            f"status: actual={explanation.status}, "
            f"expected={expectation.expected_status}"
        )

    if compare_rules:
        actual_rules = frozenset(explanation.rules)
        expected_rules = frozenset(expectation.rules)
        if actual_rules != expected_rules:
            mismatches.append(
                "rules: "
                f"actual={tuple(sorted(actual_rules))}, "
                f"expected={tuple(sorted(expected_rules))}"
            )

    return GoldenGateResult(
        case_id=expectation.case_id,
        product_code=expectation.product_code,
        passed=not mismatches,
        mismatches=tuple(mismatches),
    )


def summarize_golden_gate(
    results: Iterable[GoldenGateResult],
) -> dict[str, object]:
    values = list(results)
    failed = [item for item in values if not item.passed]
    return {
        "total": len(values),
        "passed": len(values) - len(failed),
        "failed": len(failed),
        "status": "PASS" if not failed else "FAIL",
        "failed_cases": [
            {
                "case_id": item.case_id,
                "product_code": item.product_code,
                "mismatches": list(item.mismatches),
            }
            for item in failed
        ],
    }

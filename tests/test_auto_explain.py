from __future__ import annotations

import pytest

from traceai_reconciliation.investigation.auto_explain import (
    ExplanationComponent,
    compose_explanation,
    opening_component,
)


def component(
    component_id: str,
    rule_id: str,
    effect: float,
    *,
    evidence: str = "A",
    status: str = "CONFIRMED",
    contributes: bool = True,
) -> ExplanationComponent:
    return ExplanationComponent(
        component_id=component_id,
        rule_id=rule_id,
        effect=effect,
        description=component_id,
        evidence_level=evidence,
        status=status,
        contributes=contributes,
    )


def test_exact_multi_component_equation_from_golden_pattern() -> None:
    result = compose_explanation(
        -70.0,
        [
            component("opening", "OPEN-01", -1.0),
            component("production", "PROD-02", -202.0),
            component("wme_pv", "GST-04", 140.0),
            component("delivery", "DEL-02", -7.0),
        ],
    )

    assert result.status == "EXACT"
    assert result.explained_difference == -70.0
    assert result.residual_difference == 0.0
    assert result.evidence_level == "A"
    assert result.rules == ("OPEN-01", "PROD-02", "GST-04", "DEL-02")
    assert "rezidual 0.000" in result.equation


def test_opening_only_case_is_exact() -> None:
    opening = opening_component(72.0, 76.0)
    assert opening is not None

    result = compose_explanation(-4.0, [opening])

    assert result.status == "EXACT"
    assert result.rules == ("OPEN-01",)
    assert result.residual_difference == 0.0


def test_probable_component_is_not_used_by_default() -> None:
    result = compose_explanation(
        -25.0,
        [
            component("opening", "OPEN-01", -1.0),
            component(
                "candidate_adjustment",
                "ADJ-01",
                -24.0,
                evidence="B",
                status="PROBABLE",
            ),
        ],
    )

    assert result.status == "PARTIAL"
    assert result.explained_difference == -1.0
    assert result.residual_difference == -24.0
    assert result.rules == ("OPEN-01",)


def test_probable_component_can_be_enabled_explicitly() -> None:
    result = compose_explanation(
        -25.0,
        [
            component("opening", "OPEN-01", -1.0),
            component(
                "candidate_adjustment",
                "ADJ-01",
                -24.0,
                evidence="B",
                status="PROBABLE",
            ),
        ],
        include_probable=True,
    )

    assert result.status == "EXACT"
    assert result.evidence_level == "B"
    assert result.residual_difference == 0.0


def test_non_contributing_and_review_components_do_not_change_math() -> None:
    result = compose_explanation(
        -17.0,
        [
            component("opening", "OPEN-01", -17.32),
            component("pv", "GST-04", 16.32),
            component("production", "PROD-02", -16.0),
            component(
                "timing_only",
                "TIMING",
                7.0,
                status="REVIEW",
            ),
            component(
                "matched_transfer",
                "TRANSFER",
                999.0,
                contributes=False,
            ),
        ],
    )

    assert result.status == "EXACT"
    assert result.explained_difference == -17.0
    assert result.residual_difference == 0.0


def test_duplicate_component_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="apare de mai multe ori"):
        compose_explanation(
            -10.0,
            [
                component("same", "OPEN-01", -5.0),
                component("same", "ADJ-01", -5.0),
            ],
        )


def test_wrong_direction_components_are_inconsistent() -> None:
    result = compose_explanation(
        -10.0,
        [component("wrong", "ADJ-01", 5.0)],
    )

    assert result.status == "INCONSISTENT"
    assert result.residual_difference == -15.0

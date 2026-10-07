from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


_EVIDENCE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


@dataclass(frozen=True, slots=True)
class ExplanationComponent:
    """One demonstrated contribution to the WMS-WME stock difference."""

    component_id: str
    rule_id: str
    effect: float
    description: str
    evidence_level: str = "A"
    source: str = ""
    status: str = "CONFIRMED"
    contributes: bool = True

    def __post_init__(self) -> None:
        if not self.component_id.strip():
            raise ValueError("component_id este obligatoriu.")
        if not self.rule_id.strip():
            raise ValueError("rule_id este obligatoriu.")
        if self.evidence_level not in _EVIDENCE_ORDER:
            raise ValueError(
                "evidence_level trebuie să fie unul dintre A/B/C/D."
            )


@dataclass(frozen=True, slots=True)
class AutoExplanation:
    initial_difference: float
    explained_difference: float
    residual_difference: float
    status: str
    evidence_level: str
    rules: tuple[str, ...]
    equation: str
    components: tuple[ExplanationComponent, ...]

    @property
    def exact(self) -> bool:
        return self.status == "EXACT"


def _worst_evidence(
    components: Iterable[ExplanationComponent],
) -> str:
    values = list(components)
    if not values:
        return "D"
    return max(
        (item.evidence_level for item in values),
        key=lambda value: _EVIDENCE_ORDER[value],
    )


def _format_number(value: float, decimals: int) -> str:
    rounded = round(float(value), decimals)
    if abs(rounded) < 10 ** (-decimals):
        rounded = 0.0
    return f"{rounded:.{decimals}f}"


def _equation(
    initial_difference: float,
    components: list[ExplanationComponent],
    residual: float,
    decimals: int,
) -> str:
    if not components:
        return (
            f"0 = {_format_number(initial_difference, decimals)} "
            f"(rezidual {_format_number(residual, decimals)})"
        )

    terms: list[str] = []
    for index, component in enumerate(components):
        value = round(float(component.effect), decimals)
        magnitude = _format_number(abs(value), decimals)
        if index == 0:
            prefix = "-" if value < 0 else ""
        else:
            prefix = " - " if value < 0 else " + "
        terms.append(f"{prefix}{magnitude} {component.rule_id}")

    return (
        "".join(terms)
        + f" = {_format_number(sum(c.effect for c in components), decimals)}"
        + f"; țintă {_format_number(initial_difference, decimals)}"
        + f"; rezidual {_format_number(residual, decimals)}"
    )


def compose_explanation(
    initial_difference: float,
    components: Iterable[ExplanationComponent],
    *,
    tolerance: float = 0.001,
    decimals: int = 3,
    include_probable: bool = False,
) -> AutoExplanation:
    """
    Compose a deterministic explanation from already demonstrated components.

    Safety contract:
    - CONFIRMED components are eligible by default.
    - PROBABLE components are excluded unless include_probable=True.
    - REVIEW/REJECTED components never contribute.
    - duplicate component_id values are rejected to prevent double counting.
    - this function does not infer or invent any component.
    """
    accepted_statuses = {"CONFIRMED"}
    if include_probable:
        accepted_statuses.add("PROBABLE")

    selected: list[ExplanationComponent] = []
    seen: set[str] = set()
    for component in components:
        key = component.component_id.strip()
        if key in seen:
            raise ValueError(
                f"Componenta '{key}' apare de mai multe ori; "
                "dublarea ar putea dubla explicația."
            )
        seen.add(key)

        if not component.contributes:
            continue
        if component.status not in accepted_statuses:
            continue
        if abs(float(component.effect)) <= tolerance:
            continue
        selected.append(component)

    explained = round(
        sum(float(item.effect) for item in selected),
        decimals,
    )
    residual = round(float(initial_difference) - explained, decimals)

    if abs(residual) <= tolerance:
        residual = 0.0
        status = "EXACT"
    elif abs(explained) <= tolerance:
        status = "NONE"
    elif abs(residual) < abs(float(initial_difference)) + tolerance:
        status = "PARTIAL"
    else:
        status = "INCONSISTENT"

    return AutoExplanation(
        initial_difference=round(float(initial_difference), decimals),
        explained_difference=explained,
        residual_difference=residual,
        status=status,
        evidence_level=_worst_evidence(selected),
        rules=tuple(dict.fromkeys(item.rule_id for item in selected)),
        equation=_equation(
            float(initial_difference),
            selected,
            residual,
            decimals,
        ),
        components=tuple(selected),
    )


def opening_component(
    opening_stock_wms: float | None,
    opening_stock_wme: float | None,
    *,
    decimals: int = 3,
    component_id: str = "opening_difference",
) -> ExplanationComponent | None:
    """Build the factual OPEN-01 component when both opening balances exist."""
    if opening_stock_wms is None or opening_stock_wme is None:
        return None
    effect = round(float(opening_stock_wms) - float(opening_stock_wme), decimals)
    if effect == 0:
        return None
    return ExplanationComponent(
        component_id=component_id,
        rule_id="OPEN-01",
        effect=effect,
        description=(
            "Diferență factuală între soldul de deschidere WMS și soldul "
            "de deschidere WME."
        ),
        evidence_level="A",
        source="opening_stock_wms + wme_running_balance",
        status="CONFIRMED",
    )

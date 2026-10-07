from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import ProductInvestigationResult


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



def components_from_investigation(
    result: ProductInvestigationResult,
    *,
    decimals: int = 3,
) -> list[ExplanationComponent]:
    """
    Convert only already-applied investigation components into Auto Explain
    components. This adapter does not promote REVIEW evidence and does not
    change the investigation result.
    """
    components: list[ExplanationComponent] = []

    opening = opening_component(
        result.opening_stock_wms,
        result.opening_stock_wme,
        decimals=decimals,
    )
    if opening is not None:
        components.append(opening)

    details = result.details

    zone = details.get("stock_report_zone_matching", {})
    if zone.get("applied_to_explanation", False):
        effect = round(float(zone.get("mapping_effect_total", 0.0)), decimals)
        if effect:
            components.append(
                ExplanationComponent(
                    component_id="stock_report_zone_mapping",
                    rule_id="GST-02/GST-03",
                    effect=effect,
                    description=(
                        "Efect confirmat al mapării raportului de stoc față de "
                        "soldurile WME."
                    ),
                    evidence_level="A",
                    source="stock_report_zone_matching",
                    status="CONFIRMED",
                )
            )

    production = details.get("production_matching", {})
    if production.get("applied_to_explanation", False):
        effect = round(float(production.get("residual_total", 0.0)), decimals)
        if effect:
            residual_items = list(
                production.get("residual_adjustment_items", []) or []
            )
            generic_tokens = (
                "CARTOANE DEFECTE",
                "NOTA DE CREDIT",
                "NOTĂ DE CREDIT",
                "INVENTAR",
                "PROCES VERBAL",
                "RETUR FACTURAT",
            )
            texts = [
                " ".join(
                    [
                        str(item.get("cod_motiv", "")),
                        str(item.get("details", "")),
                    ]
                ).upper()
                for item in residual_items
            ]
            clearly_generic = bool(texts) and all(
                any(token in text for token in generic_tokens)
                for text in texts
            )
            rule_id = "ADJ-01" if clearly_generic else "PROD-02"
            component_id = (
                "production_location_generic_adjustment"
                if clearly_generic
                else "production_residual"
            )
            description = (
                "COR STOC WMS rezidual în locație de producție, dar cu motiv "
                "explicit non-producție; clasificat ca ADJ-01."
                if clearly_generic
                else "Ajustare reziduală WMS din locația/fluxul de producție, "
                "păstrată PROD-02 în lipsa unui motiv explicit non-producție."
            )
            components.append(
                ExplanationComponent(
                    component_id=component_id,
                    rule_id=rule_id,
                    effect=effect,
                    description=description,
                    evidence_level="B",
                    source="production_matching",
                    status="CONFIRMED",
                )
            )
    else:
        document_residuals = list(
            production.get("document_residuals", []) or []
        )
        if len(document_residuals) == 1:
            effect = round(
                float(
                    document_residuals[0].get(
                        "effective_difference",
                        production.get("document_residual_total", 0.0),
                    )
                ),
                decimals,
            )
            current_explained = round(
                sum(float(item.effect) for item in components),
                decimals,
            )
            candidate = round(current_explained + effect, decimals)
            same_direction = (
                effect != 0
                and result.initial_difference != 0
                and (effect > 0) == (result.initial_difference > 0)
            )
            bounded = (
                abs(candidate)
                <= abs(float(result.initial_difference)) + 10 ** (-decimals)
            )
            if same_direction and bounded:
                components.append(
                    ExplanationComponent(
                        component_id="production_document_residual",
                        rule_id="PROD-02",
                        effect=effect,
                        description=(
                            "Diferență cantitativă unică WMS PRODUCTION-OUT "
                            "față de NP WME rămasă după eliminarea ordinelor "
                            "WMS complet reversate."
                        ),
                        evidence_level="B",
                        source="production_matching.document_residuals",
                        status="CONFIRMED",
                    )
                )

    production_input = details.get("production_input_matching", {})
    if production_input.get("applied_to_explanation", False):
        effect = round(
            float(production_input.get("residual_total", 0.0)),
            decimals,
        )
    elif production_input.get("safe_to_auto_explain", False):
        effect = round(
            float(production_input.get("persistent_residual_total", 0.0)),
            decimals,
        )
    else:
        effect = 0.0

    if effect:
        components.append(
            ExplanationComponent(
                component_id="production_input_persistent_residual",
                rule_id="PROD-03",
                effect=effect,
                description=(
                    "Rezidual persistent PRODUCTION-IN↔BC după excluderea "
                    "reversărilor PROD-05, a diferențelor anterioare ultimului "
                    "checkpoint de inventar și a neutralizărilor COR STOC "
                    "explicite; consumul este confirmat de raportul de producție."
                ),
                evidence_level="A",
                source="production_input_matching.persistent_residual_total",
                status="CONFIRMED",
            )
        )

    delivery = details.get("delivery_matching", {})
    wme_residual = details.get("wme_residual_movements", {})
    wme_movements = list(wme_residual.get("movements", []) or [])
    neutralized_wme_indices: set[int] = set()
    delivery_effect = round(float(delivery.get("residual_total", 0.0)), decimals)
    tolerance = 10 ** (-decimals)
    pre_delivery_explained = round(
        sum(float(item.effect) for item in components),
        decimals,
    )
    pre_delivery_residual = round(
        float(result.initial_difference) - pre_delivery_explained,
        decimals,
    )
    suppress_delivery = abs(pre_delivery_residual) <= tolerance

    # Conservative bridge: an exact one-to-one opposite PV WME can neutralize
    # a delivery residual as document-family/timing evidence. F movements are
    # intentionally excluded and multiple candidates remain REVIEW.
    if delivery_effect:
        opposite_pv = [
            index
            for index, item in enumerate(wme_movements)
            if str(item.get("operation_type", "")).strip().upper() == "PV"
            and abs(
                round(
                    float(item.get("system_difference_effect", 0.0)),
                    decimals,
                )
                + delivery_effect
            )
            <= tolerance
        ]
        if len(opposite_pv) == 1:
            neutralized_wme_indices.add(opposite_pv[0])
            suppress_delivery = True

    if delivery.get("applied_to_explanation", False) and not suppress_delivery:
        effect = delivery_effect
        if effect:
            components.append(
                ExplanationComponent(
                    component_id="delivery_residual",
                    rule_id="DEL-02",
                    effect=effect,
                    description=(
                        "Diferență reziduală după netarea livrărilor/retururilor "
                        "WMS față de AE WME."
                    ),
                    evidence_level="B",
                    source="delivery_matching",
                    status="CONFIRMED",
                )
            )

    correction = details.get("generic_stock_corrections", {})
    special = details.get("special_status_matching", {})

    # Flow-specific evidence has priority over a generic COR STOC. If the
    # special-status component closes the current residual exactly, do not
    # double-count a weaker generic adjustment that the legacy engine happened
    # to apply earlier in its ordering.
    current_before_generic = round(
        sum(float(item.effect) for item in components),
        decimals,
    )
    residual_before_generic = round(
        float(result.initial_difference) - current_before_generic,
        decimals,
    )
    special_effect = round(
        float(special.get("explained_total", 0.0)),
        decimals,
    )
    special_closes_residual = (
        special.get("applied_to_explanation", False)
        and abs(special_effect - residual_before_generic) <= tolerance
    )
    if (
        correction.get("applied_to_explanation", False)
        and abs(residual_before_generic) > tolerance
        and not special_closes_residual
    ):
        effect = round(float(correction.get("residual_total", 0.0)), decimals)
        if effect:
            components.append(
                ExplanationComponent(
                    component_id="generic_stock_correction",
                    rule_id="ADJ-01",
                    effect=effect,
                    description=(
                        "COR STOC WMS rezidual deja aplicat de motor la "
                        "diferența explicată."
                    ),
                    evidence_level="B",
                    source="generic_stock_corrections",
                    status="CONFIRMED",
                )
            )

    if special.get("applied_to_explanation", False):
        effect = round(float(special.get("explained_total", 0.0)), decimals)
        if effect:
            components.append(
                ExplanationComponent(
                    component_id="special_status_residual",
                    rule_id="GST-04",
                    effect=effect,
                    description=(
                        "Efect rezidual al fluxului special validat și deja "
                        "aplicat de motor."
                    ),
                    evidence_level="B",
                    source="special_status_matching",
                    status="CONFIRMED",
                )
            )

    # WME-02: after stronger components and exact delivery/PV
    # neutralizations, a single remaining PV may contribute only when its
    # system-difference effect closes the current residual exactly.
    current_explained = round(
        sum(float(item.effect) for item in components),
        decimals,
    )
    current_residual = round(
        float(result.initial_difference) - current_explained,
        decimals,
    )
    pv_closure_candidates = [
        (index, item)
        for index, item in enumerate(wme_movements)
        if index not in neutralized_wme_indices
        and str(item.get("operation_type", "")).strip().upper() == "PV"
        and abs(
            round(
                float(item.get("system_difference_effect", 0.0)),
                decimals,
            )
            - current_residual
        )
        <= tolerance
        and abs(current_residual) > tolerance
    ]
    if len(pv_closure_candidates) == 1:
        _, item = pv_closure_candidates[0]
        effect = round(
            float(item.get("system_difference_effect", 0.0)),
            decimals,
        )
        components.append(
            ExplanationComponent(
                component_id=(
                    "wme_pv_exact_closure_"
                    + str(item.get("document", "-"))
                    + "_"
                    + str(item.get("warehouse", "-"))
                ),
                rule_id="WME-02",
                effect=effect,
                description=(
                    "PV WME rezidual, unic după neutralizările exacte, al cărui "
                    "efect WMS-WME închide exact rezidualul curent."
                ),
                evidence_level="B",
                source="wme_residual_movements",
                status="CONFIRMED",
            )
        )

    return components


def auto_explanation_from_investigation(
    result: ProductInvestigationResult,
    *,
    tolerance: float = 0.001,
    decimals: int = 3,
) -> AutoExplanation:
    """Compose a non-mutating Auto Explain view of an investigation result."""
    return compose_explanation(
        result.initial_difference,
        components_from_investigation(result, decimals=decimals),
        tolerance=tolerance,
        decimals=decimals,
    )


def auto_explanation_to_dict(
    explanation: AutoExplanation,
) -> dict[str, object]:
    return {
        "initial_difference": explanation.initial_difference,
        "explained_difference": explanation.explained_difference,
        "residual_difference": explanation.residual_difference,
        "status": explanation.status,
        "evidence_level": explanation.evidence_level,
        "rules": list(explanation.rules),
        "equation": explanation.equation,
        "components": [
            {
                "component_id": item.component_id,
                "rule_id": item.rule_id,
                "effect": item.effect,
                "description": item.description,
                "evidence_level": item.evidence_level,
                "source": item.source,
                "status": item.status,
                "contributes": item.contributes,
            }
            for item in explanation.components
        ],
    }

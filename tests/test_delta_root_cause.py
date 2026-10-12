from traceai_reconciliation.investigation.delta_movement_window import (
    DeltaMovementWindowResult,
)
from traceai_reconciliation.investigation.delta_root_cause import (
    analyze_delta_root_cause,
)


def _window(*, wms_rows=(), wme_rows=(), production_rows=()):
    return DeltaMovementWindowResult(
        product_code="DS099904475",
        product_name="Produs test",
        start_exclusive="2026-10-11T20:00:00",
        end_inclusive="2026-10-12T20:00:00",
        wms_count=len(wms_rows),
        wme_count=len(wme_rows),
        production_count=len(production_rows),
        wms_rows=tuple(wms_rows),
        wme_rows=tuple(wme_rows),
        production_rows=tuple(production_rows),
    )


def test_exact_event_explains_ds099904475_style_delta() -> None:
    result = analyze_delta_root_cause(
        movement_window=_window(
            wms_rows=(
                {
                    "Data": "2026-10-12 10:00:00",
                    "Cantitate": -1.44,
                    "Numar comanda": "ADJ-TEST",
                    "Tip operatiune": "AJUSTARE",
                },
            )
        ),
        previous_difference=62.9,
        current_difference=61.46,
    )

    assert result.status == "EXACT_EVENT"
    assert round(result.observed_delta, 6) == -1.44
    assert round(result.explained_delta, 6) == -1.44
    assert round(result.residual_delta, 6) == 0.0
    assert len(result.evidence) == 1
    assert result.evidence[0].source == "WMS"


def test_wme_signed_quantity_has_inverse_effect_on_difference() -> None:
    result = analyze_delta_root_cause(
        movement_window=_window(
            wme_rows=(
                {
                    "Date": "2026-10-12 10:00:00",
                    "SignedQuantity": 2.0,
                    "Document": "FE-1",
                    "OperationType": "FE",
                },
            )
        ),
        previous_difference=10.0,
        current_difference=8.0,
    )

    assert result.status == "EXACT_EVENT"
    assert result.explained_delta == -2.0


def test_multi_event_explains_combined_delta() -> None:
    result = analyze_delta_root_cause(
        movement_window=_window(
            wms_rows=(
                {"Data": "2026-10-12 09:00:00", "Cantitate": -1.0},
                {"Data": "2026-10-12 10:00:00", "Cantitate": -0.44},
            )
        ),
        previous_difference=62.9,
        current_difference=61.46,
    )

    assert result.status == "MULTI_EVENT"
    assert round(result.explained_delta, 6) == -1.44
    assert round(result.residual_delta, 6) == 0.0


def test_unexplained_does_not_force_match() -> None:
    result = analyze_delta_root_cause(
        movement_window=_window(
            wms_rows=(
                {"Data": "2026-10-12 09:00:00", "Cantitate": -1.0},
            )
        ),
        previous_difference=62.9,
        current_difference=61.46,
    )

    assert result.status == "UNEXPLAINED"
    assert round(result.residual_delta, 6) == -0.44


def test_production_is_context_only_not_double_counted() -> None:
    result = analyze_delta_root_cause(
        movement_window=_window(
            wms_rows=(
                {"Data": "2026-10-12 09:00:00", "Cantitate": -1.44},
            ),
            production_rows=(
                {"Data Start": "2026-10-12 09:05:00", "Qty": -1.44},
            ),
        ),
        previous_difference=62.9,
        current_difference=61.46,
    )

    assert result.status == "EXACT_EVENT"
    assert round(result.explained_delta, 6) == -1.44

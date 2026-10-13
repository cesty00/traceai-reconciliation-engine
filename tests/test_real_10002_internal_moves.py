"""Real WMS 10002 regression, exported 2026-10-11.
These records are selected from item 10002 WMS traceability, not synthetic
quantity ratios. The source correction and internal moves have distinct dates.
The test checks economic treatment, not a full stock-snapshot reconstruction.
"""
from traceai_reconciliation.investigation.delta_movement_window import DeltaMovementWindowResult
from traceai_reconciliation.investigation.delta_root_cause import analyze_delta_root_cause


def test_10002_real_internal_move_does_not_create_aggregate_stock():
    rows = (
        {"Data": "2026-07-23 08:28:20", "Tip operatiune": "Mutare intre gestiuni", "Cantitate": 450.0, "Numar comanda": "M19__0E7303F7"},
        {"Data": "2026-07-23 08:28:26", "Tip operatiune": "Mutare intre gestiuni", "Cantitate": 450.0, "Numar comanda": "M19__0E7303F7"},
        {"Data": "2026-07-23 08:28:34", "Tip operatiune": "Mutare intre gestiuni", "Cantitate": 450.0, "Numar comanda": "M19__0E7303F7"},
        {"Data": "2026-07-23 08:28:42", "Tip operatiune": "Mutare intre gestiuni", "Cantitate": 350.0, "Numar comanda": "M19__0E7303F7"},
    )
    window = DeltaMovementWindowResult(
        product_code="10002", product_name="CUTIE FRESH DIM INTERIOARA 342x342x208MM",
        start_exclusive="2026-07-22T20:00:00", end_inclusive="2026-07-23T20:00:00",
        wms_count=len(rows), wme_count=0, production_count=0,
        wms_rows=rows, wme_rows=(), production_rows=(),
    )
    result = analyze_delta_root_cause(
        movement_window=window, previous_difference=-872.0, current_difference=-872.0, stock_scope="AGGREGATE"
    )
    assert result.observed_delta == 0.0
    assert result.explained_delta == 0.0
    assert result.residual_delta == 0.0
    assert result.status == "UNEXPLAINED"
    assert len(result.evidence) == 0


def test_10002_internal_move_unknown_scope_fails_closed():
    rows = ({"Data": "2026-07-23 08:28:20",
             "Tip operatiune": "Mutare intre gestiuni",
             "Cantitate": 450.0},)
    window = DeltaMovementWindowResult(
        product_code="10002", product_name="CUTIE FRESH",
        start_exclusive="2026-07-22T20:00:00",
        end_inclusive="2026-07-23T20:00:00",
        wms_count=1, wme_count=0, production_count=0,
        wms_rows=rows, wme_rows=(), production_rows=(),
    )
    finding = analyze_delta_root_cause(
        movement_window=window,
        previous_difference=0.0, current_difference=450.0,
    )
    assert finding.status == "UNEXPLAINED"
    assert finding.residual_delta == 450.0
    assert "TRANSFER_SCOPE_UNVERIFIED" in finding.note
    assert len(finding.evidence) == 1

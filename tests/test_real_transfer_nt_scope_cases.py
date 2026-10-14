"""Real transfer candidate regression rows from WMS/WME October 11 exports.

Tests do not certify the cross-system warehouse mapping.
"""
from traceai_reconciliation.investigation.delta_movement_window import DeltaMovementWindowResult
from traceai_reconciliation.investigation.delta_root_cause import analyze_delta_root_cause


def _window(code, wms, wme):
    return DeltaMovementWindowResult(
        product_code=code, product_name=code,
        start_exclusive="2026-03-20T00:00:00",
        end_inclusive="2026-03-31T00:00:00",
        wms_count=len(wms),wme_count=len(wme),production_count=0,
        wms_rows=tuple(wms),wme_rows=tuple(wme),production_rows=(),
    )


def test_50005_nt19462_has_zero_aggregate_effect():
    wms=[{"Data":"2026-03-21","Tip operatiune":"Mutare intre gestiuni",
          "Numar comanda":"M8__03C19521","Cantitate":96000,
          "Locatie sursa":"DEPAMBF","Locatie destinatie":"DEPAMB"}]
    wme=[
        {"Date":"2026-03-21","OperationType":"NT","Document":"19462",
         "Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":-64000},
        {"Date":"2026-03-21","OperationType":"NT","Document":"19462",
         "Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":-32000},
        {"Date":"2026-03-21","OperationType":"NT","Document":"19462",
         "Warehouse":"SECTIE PRODUCTIE","SignedQuantity":32000},
        {"Date":"2026-03-21","OperationType":"NT","Document":"19462",
         "Warehouse":"SECTIE PRODUCTIE","SignedQuantity":64000},
    ]
    res=analyze_delta_root_cause(
        movement_window=_window("50005",wms,wme),
        previous_difference=0,current_difference=0,stock_scope="AGGREGATE")
    assert res.explained_delta==0
    assert res.residual_delta==0
    assert sum(e.quantity for e in res.evidence if e.source=="WME")==0


def test_ds099904183_nt20338_does_not_absorb_cor_stoc_minus18():
    wms=[
        {"Data":"2026-03-30 15:45:51","Tip operatiune":"Mutare intre gestiuni",
         "Numar comanda":"M8__42585A40","Cantitate":68,
         "Locatie sursa":"MASA","Locatie destinatie":"DEP100"},
        {"Data":"2026-03-30 15:48:07","Tip operatiune":"Ajustare negativa",
         "Cod-motiv":"COR STOC","Cantitate":-18,
         "Locatie sursa":"DEP100","Locatie destinatie":"DEP100"},
    ]
    wme=[
        {"Date":"2026-03-30","OperationType":"NT","Document":"20338",
         "Warehouse":"SECTIE PRODUCTIE","SignedQuantity":-68},
        {"Date":"2026-03-30","OperationType":"NT","Document":"20338",
         "Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":68},
    ]
    res=analyze_delta_root_cause(
        movement_window=_window("DS099904183",wms,wme),
        previous_difference=0,current_difference=-18,stock_scope="AGGREGATE")
    assert res.explained_delta==-18
    assert res.residual_delta==0
    assert any(e.difference_effect==-18 for e in res.evidence)
    assert all(e.difference_effect==0 for e in res.evidence if e.operation_type=="Mutare intre gestiuni")

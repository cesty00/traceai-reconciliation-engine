"""Real 10002 2026-02-18 documentary chain, transcribed from WMS/WME exports.
This is an arithmetic integration regression, not global warehouse-map approval.
"""
from traceai_reconciliation.investigation.delta_movement_window import DeltaMovementWindowResult
from traceai_reconciliation.investigation.delta_root_cause import analyze_delta_root_cause


def test_10002_f7163109_nt9833_chain_nets_without_double_stock():
    wms = tuple(
        {"Data":"2026-02-18 15:51:37","Tip operatiune":"Receptie",
         "Cantitate":450.0,"Numar comanda":"IN3013",
         "Document intrare":"7163109","Locatie destinatie":"REC100"}
        for _ in range(11)
    ) + tuple(
        {"Data":"2026-02-18 15:57:14","Tip operatiune":"Mutare intre gestiuni",
         "Cantitate":450.0,"Numar comanda":"M19__6CE4F19F",
         "Locatie sursa":"REC100","Locatie destinatie":"DEPAMBE"}
        for _ in range(11)
    )
    wme = (
        {"Date":"2026-02-18","OperationType":"F","Document":"7163109",
         "Warehouse":"SECTIE PRODUCTIE","SignedQuantity":4950.0},
        {"Date":"2026-02-18","OperationType":"NT","Document":"9833",
         "Warehouse":"SECTIE PRODUCTIE","SignedQuantity":-4950.0},
        {"Date":"2026-02-18","OperationType":"NT","Document":"9833",
         "Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":4950.0},
    )
    window = DeltaMovementWindowResult(
        product_code="10002",product_name="CUTIE FRESH DIM INTERIOARA 342x342x208MM",
        start_exclusive="2026-02-17T20:00:00",end_inclusive="2026-02-18T20:00:00",
        wms_count=len(wms),wme_count=len(wme),production_count=0,
        wms_rows=wms,wme_rows=wme,production_rows=(),
    )
    result = analyze_delta_root_cause(
        movement_window=window,previous_difference=0,current_difference=0,
        stock_scope="AGGREGATE",
    )
    assert result.explained_delta == 0
    assert result.residual_delta == 0
    assert sum(e.difference_effect for e in result.evidence if e.source=="WMS")==4950
    assert sum(e.difference_effect for e in result.evidence if e.source=="WME")==-4950
    assert sum(e.quantity for e in result.evidence if e.source=="WME" and e.operation_type=="NT")==0

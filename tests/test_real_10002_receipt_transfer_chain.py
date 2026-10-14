"""Regression from actual item 10002 events in 2026-10-11 exports.
These are manually extracted rows, not a complete end-to-end source-import test.
"""
from traceai_reconciliation.investigation.delta_movement_window import DeltaMovementWindowResult
from traceai_reconciliation.investigation.delta_root_cause import analyze_delta_root_cause


def test_receipt_7174230_and_later_internal_move_are_not_double_counted():
    wms_receipt = [
        {"Data":"2026-07-21 14:13:49","Tip operatiune":"Receptie","Cantitate":q,
         "Document intrare":"7174230","Locatie destinatie":"REC100"}
        for q in (450.0,450.0,450.0,350.0)
    ]
    wms_move = [
        {"Data":"2026-07-23 08:28:20","Tip operatiune":"Mutare intre gestiuni",
         "Cantitate":q,"Numar comanda":"M19__0E7303F7",
         "Locatie sursa":"REC100","Locatie destinatie":"DEPAMBF"}
        for q in (450.0,450.0,450.0,350.0)
    ]
    wme_receipt = ({"Date":"2026-07-21","OperationType":"F","Document":"7174230",
                    "Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":1700.0},)
    window=DeltaMovementWindowResult(
        product_code="10002",product_name="CUTIE FRESH DIM INTERIOARA 342x342x208MM",
        start_exclusive="2026-07-20T20:00:00",end_inclusive="2026-07-23T20:00:00",
        wms_count=8,wme_count=1,production_count=0,
        wms_rows=tuple(wms_receipt+wms_move),wme_rows=wme_receipt,production_rows=(),
    )
    result=analyze_delta_root_cause(
        movement_window=window,previous_difference=0.0,current_difference=0.0,
        stock_scope="AGGREGATE",
    )
    assert result.observed_delta == 0.0
    assert result.explained_delta == 0.0
    assert result.residual_delta == 0.0
    assert sum(item.difference_effect for item in result.evidence if item.source=="WMS")==1700.0
    assert sum(item.difference_effect for item in result.evidence if item.source=="WME")==-1700.0
    assert all(item.difference_effect==0 for item in result.evidence if item.operation_type=="Mutare intre gestiuni")

import pandas as pd
from traceai_reconciliation.investigation.inventory_adjustment_matching import match_inventory_adjustments

def test_real_export_document_alias_is_retained_but_numeric_format_flagged():
    wms=pd.DataFrame([{"Data":"10.10.2026","Tip operatiune":"Ajustare negativa",
        "Cantitate":-131.75,"Cod-motiv":"INV-MIN",
        "Document intrare":60.0,"Lot":"SYN-LOT"}])
    result=match_inventory_adjustments(wms,pd.DataFrame())
    item=result.residual_wms_adjustments[0]["contributing_event_refs"][0]
    assert item["document"]=="60.0"
    assert item["document_format_status"]=="LOSSY_NUMERIC_IMPORT"
    assert item["source_pointer_status"]=="UNVERIFIED"

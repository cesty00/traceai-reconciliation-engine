"""Approved read-only CORE INV-01 extension regression."""
import pandas as pd
from traceai_reconciliation.investigation.inventory_adjustment_matching import match_inventory_adjustments

def rows():
    return pd.DataFrame([
        {"Data":"10.10.2026","Tip operatiune":"Ajustare negativa","Cantitate":-131.75,"Cod-motiv":"INV-MIN","Document":"SYN-00060","Lot":"A"},
        {"Data":"10.10.2026","Tip operatiune":"Ajustare negativa","Cantitate":-0.25,"Cod-motiv":"INV-MIN","Document":"SYN-00061","Lot":"B"},
        {"Data":"10.10.2026","Tip operatiune":"Ajustare pozitiva","Cantitate":45.65,"Cod-motiv":"INV-PLS","Document":"SYN-00060","Lot":"C"},
    ])

def test_preserves_docs_lots_and_economics():
    result=match_inventory_adjustments(rows(),pd.DataFrame())
    assert result.system_difference_effect == -86.35
    events=[e for g in result.residual_wms_adjustments for e in g["contributing_event_refs"]]
    assert len(events)==3
    assert {e["document"] for e in events}=={"SYN-00060","SYN-00061"}
    assert {e["lot"] for e in events}=={"A","B","C"}
    assert all(e["source_pointer_status"]=="UNVERIFIED" for e in events)
    assert result.residual_wms_total==-86.35
    assert result.residual_wme_total==0

def test_missing_optional_document_is_not_guessed():
    result=match_inventory_adjustments(rows().drop(columns=["Document","Lot"]),pd.DataFrame())
    events=[e for g in result.residual_wms_adjustments for e in g["contributing_event_refs"]]
    assert len(events)==3
    assert all(e["document"] is None and e["lot"] is None for e in events)

def test_existing_pv_neutralization_remains():
    wms=pd.DataFrame([{"Data":"10.10.2026","Tip operatiune":"Ajustare negativa",
                      "Cantitate":-5,"Cod-motiv":"INV-MIN","Document":"SYN-01","Lot":"A"}])
    wme=pd.DataFrame([{"Date":"10.10.2026","OperationType":"PV","SignedQuantity":-5,
                       "Document":"SYN-PV","Warehouse":"SYN-WH"}])
    result=match_inventory_adjustments(wms,wme)
    assert len(result.matches)==1
    assert result.system_difference_effect==0
    assert result.residual_wms_adjustments==[]

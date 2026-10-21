"""CORE-UAT-04F isolated sidecar versus unchanged matcher regression."""
import importlib.util
from pathlib import Path
import pandas as pd
from traceai_reconciliation.investigation.inventory_adjustment_matching import match_inventory_adjustments

p=Path(__file__).parents[1]/"prototypes/core_uat_03/inventory_group_sidecar.py"
s=importlib.util.spec_from_file_location("sidecar",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def sample():
    return pd.DataFrame([
        {"Data":"10.10.2026","Tip operatiune":"Ajustare negativa","Cantitate":-131.75,"Cod-motiv":"INV-MIN","Document":"00060","Lot":"LOT-A"},
        {"Data":"10.10.2026","Tip operatiune":"Ajustare negativa","Cantitate":-0.25,"Cod-motiv":"INV-MIN","Document":"00060","Lot":"LOT-B"},
        {"Data":"10.10.2026","Tip operatiune":"Ajustare pozitiva","Cantitate":45.65,"Cod-motiv":"INV-PLS","Document":"00060","Lot":"LOT-C"},
    ])

def test_docs_and_lots_survive_without_altering_matcher():
    wms=sample()
    baseline=match_inventory_adjustments(wms,pd.DataFrame())
    sidecar=m.inventory_group_sidecar(wms)
    assert round(sum(x["quantity"] for x in sidecar),2)==-86.35
    assert sum(len(x["contributing_events"]) for x in sidecar)==3
    assert {e["lot"] for g in sidecar for e in g["contributing_events"]}=={"LOT-A","LOT-B","LOT-C"}
    after=match_inventory_adjustments(wms,pd.DataFrame())
    assert baseline==after
    assert round(after.system_difference_effect,2)==-86.35

def test_distinct_documents_same_day_reason_remain_distinct():
    wms=sample()
    wms.loc[1,"Document"]="00061"
    sidecar=m.inventory_group_sidecar(wms)
    docs={e["document"] for g in sidecar for e in g["contributing_events"]}
    assert docs=={"00060","00061"}
    assert round(sum(g["quantity"] for g in sidecar),2)==-86.35

def test_unverified_rows_not_promoted():
    sidecar=m.inventory_group_sidecar(sample())
    assert all(e["source_pointer_status"]=="UNVERIFIED" for g in sidecar for e in g["contributing_events"])

def test_missing_lot_column_fails_closed():
    import pytest
    with pytest.raises(ValueError):
        m.inventory_group_sidecar(sample().drop(columns=["Lot"]))

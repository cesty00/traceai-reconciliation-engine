import pandas as pd
import pytest
from traceai_reconciliation.operator_stock_view import build_warehouse_stock_view

def test_all_gestiuni_are_visible_with_distinct_balances():
    report = pd.DataFrame([
      dict(CodArticol="10002",DenumireArticol="CUTIE FRESH",Gestiune="Depozitare",QuantityWMS=6090,QuantityERP=6961.9999),
      dict(CodArticol="10002",DenumireArticol="CUTIE FRESH",Gestiune="SECTIE PRODUCTIE",QuantityWMS=166.98,QuantityERP=166.98),
      dict(CodArticol="OTHER",DenumireArticol="Other",Gestiune="Depozitare",QuantityWMS=12,QuantityERP=12),
    ])
    view=build_warehouse_stock_view(report)
    two=view[view.CodArticol=="10002"]
    assert len(two)==2
    assert set(two.Gestiune)=={"Depozitare","SECTIE PRODUCTIE"}
    assert abs(two.Diferenta_WMS_minus_WME.sum()+871.9999)<0.001
    assert (two.Diferenta_WMS_minus_WME.abs()<0.001).any()

def test_missing_warehouse_fails_closed():
    report=pd.DataFrame([dict(CodArticol="10002",DenumireArticol="CUTIE",Gestiune=None,QuantityWMS=1,QuantityERP=1)])
    with pytest.raises(ValueError,match="Gestiune lipsă"):
        build_warehouse_stock_view(report)

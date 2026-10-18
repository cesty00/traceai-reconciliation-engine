import pandas as pd
from traceai_reconciliation.operator_stock_view import build_depozitare_consolidated_view

def test_reception_is_staging_inside_storage_not_an_extra_warehouse():
    detail = pd.DataFrame([
        {"CodArticol":"DS056405133","Gestiune":"Depozitare","WMS":23380,"WME":24280},
        {"CodArticol":"DS056405133","Gestiune":"Recepție","WMS":900,"WME":0},
        {"CodArticol":"DS056405133","Gestiune":"MOSE","WMS":20,"WME":20},
    ])
    output = build_depozitare_consolidated_view(detail)
    assert len(output)==1
    assert output.iloc[0]["WMS"]==24280
    assert output.iloc[0]["WME"]==24280
    assert output.iloc[0]["Diferenta_WMS_minus_WME"]==0
    assert len(detail)==3

def test_other_warehouses_remain_outside_reception_scope():
    detail = pd.DataFrame([{"CodArticol":"X","Gestiune":"SECȚIE PRODUCȚIE","WMS":2,"WME":0}])
    assert build_depozitare_consolidated_view(detail).empty

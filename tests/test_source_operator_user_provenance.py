import pandas as pd
from traceai_reconciliation.investigation.operation_timeline import _source_actor, timeline_from_wms
from traceai_reconciliation.reports.operator_causes_report import _actor_label

def test_explicit_user_and_person_provenance():
    row=pd.Series({"User":"oper_17","Nume operator":"Operator Test"})
    assert _source_actor(row)=={"user":"oper_17","person":"Operator Test"}
    assert _actor_label({"actor":_source_actor(row)})=="Operator Test / oper_17"

def test_no_attribution_from_partner_or_warehouse():
    row=pd.Series({"Partner":"Furnizor","Warehouse":"SECTIE PRODUCTIE","Coloana":"abc"})
    assert _source_actor(row)=={}
    assert _actor_label({"actor":{}})=="Nedisponibil în sursă"

def test_wms_timeline_retains_explicit_operator():
    df=pd.DataFrame([{"Data":"2026-08-12","Tip operatiune":"Ajustare negativa",
         "Cantitate":-8620,"Document":"-","Gestiune":"Depozit Principal",
         "Cod articol":"40024","SourceRowNumber":275716,"Utilizator":"wms17"}])
    entries=timeline_from_wms(df)
    assert entries[0]["actor"]=={"user":"wms17"}
    assert entries[0]["source_row"]==275716

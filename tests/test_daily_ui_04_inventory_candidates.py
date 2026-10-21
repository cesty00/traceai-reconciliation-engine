from traceai_reconciliation.daily_ui.inventory_candidates import inventory_document_candidates
from traceai_reconciliation.daily_ui.read_model import operator_view
def case():
 return {"details":{"inventory_adjustment_matching":{"residual_wms_adjustments":[
 {"reason":"INV-MIN","quantity":-132.0,"contributing_event_refs":[{"document":"SYN-60","lot":"A","quantity":-131.75},{"document":"SYN-60","lot":"B","quantity":-0.25}]},
 {"reason":"INV-PLS","quantity":45.65,"contributing_event_refs":[{"document":"SYN-60","lot":"C","quantity":45.65}]}]}}}
def test_candidate_groups_three_rows_by_document():
 c=inventory_document_candidates(case())
 assert len(c)==1 and c[0]["document"]=="SYN-60"
 assert round(sum(e["quantity"] for e in c[0]["events"]),2)==-86.35
 assert all(e["source_status"]=="UNVERIFIED" for e in c[0]["events"])
def test_missing_document_not_invented():
 d=case();d["details"]["inventory_adjustment_matching"]["residual_wms_adjustments"][0]["contributing_event_refs"][0]["document"]=None
 assert sum(len(x["events"]) for x in inventory_document_candidates(d))==2
def test_no_inventory_details_is_backward_compatible():
 assert inventory_document_candidates({"details":{}})==[]

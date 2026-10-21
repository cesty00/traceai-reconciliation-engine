from traceai_reconciliation.daily_ui.inventory_candidates import inventory_document_candidates
def test_real_self_service_nested_shape():
 d={"investigation":{"case_id":"SYN","details":{"inventory_adjustment_matching":{"residual_wms_adjustments":[{"contributing_event_refs":[{"document":"SYN-60","lot":"A","quantity":-5}]}]}}}}
 c=inventory_document_candidates(d)
 assert len(c)==1 and c[0]["document"]=="SYN-60"
def test_nested_legacy_without_refs_fails_closed_empty():
 d={"investigation":{"case_id":"SYN","details":{"inventory_adjustment_matching":{"residual_wms_adjustments":[{"quantity":-5}]}}}}
 assert inventory_document_candidates(d)==[]

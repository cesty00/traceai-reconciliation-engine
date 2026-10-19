import json
from pathlib import Path
from traceai_reconciliation.client_config.contract import validate_profile_dict
from traceai_reconciliation.client_config.normalizer import normalize_rows

ROOT = Path(__file__).resolve().parents[1] / "examples" / "client_profiles"
def profile(name):
    return validate_profile_dict(json.loads((ROOT / name).read_text(encoding="utf8")))

def test_demo_a_wms_is_normalized_without_reconciliation():
    p=profile("demo_a_wms_erp.json")
    x=normalize_rows(p,"warehouse_export",[{"SKU":"SYN-1","MovedQty":"-10.50","OrderRef":"FICT-001","Site":"DC_NORTH"}])
    assert x["rows"][0]["warehouse"]=="MAIN"
    assert x["rows"][0]["quantity"]=="-10.50"
    assert x["status"]=="NORMALIZED_NOT_RECONCILED"
    assert x["matching_performed"] is False

def test_demo_b_3pl_uses_same_function_with_other_columns():
    p=profile("demo_b_3pl_excel.json")
    x=normalize_rows(p,"third_party_log",[{"ExternalItem":"FAKE-9","UnitsDelta":4,
        "MovementId":"SIM-200","Zone":"ZONE_X"}])
    assert x["rows"][0]["product_code"]=="FAKE-9"
    assert x["rows"][0]["warehouse"]=="MAIN"

def test_invalid_quantity_is_rejected_not_guessed():
    p=profile("demo_a_wms_erp.json")
    x=normalize_rows(p,"warehouse_export",[{"SKU":"SYN-1","MovedQty":"1,234",
       "OrderRef":"FICT-001","Site":"DC_NORTH"}])
    assert not x["rows"]
    assert x["rejected"][0]["reason"]=="INVALID_QUANTITY"

def test_missing_column_is_rejected_and_row_keeps_source_position():
    p=profile("demo_a_wms_erp.json")
    x=normalize_rows(p,"warehouse_export",[{"SKU":"SYN-1","MovedQty":1,
       "OrderRef":"FICT-001"}])
    assert x["rejected"]==[{"source_row":1,"reason":"MISSING_SOURCE_COLUMN"}]

def test_unknown_source_cannot_normalize():
    import pytest
    with pytest.raises(ValueError):
        normalize_rows(profile("demo_a_wms_erp.json"),"unknown",[])

"""TRACEAI-EXT-004 synthetic CSV ingestion and row-level provenance."""
import csv
import json
from pathlib import Path
from traceai_reconciliation.client_config.contract import validate_profile_dict
from traceai_reconciliation.client_config.normalizer import normalize_rows

ROOT = Path(__file__).resolve().parents[1] / "examples"
def fixture(profile_name, file_name):
    p=validate_profile_dict(json.loads((ROOT/"client_profiles"/profile_name).read_text(encoding="utf-8")))
    with (ROOT/"synthetic_exports"/file_name).open(encoding="utf-8", newline="") as f:
        data=list(csv.DictReader(f))
    return p, data

def test_demo_a_end_to_end_normalization():
    p, rows=fixture("demo_a_wms_erp.json","demo_a_wms.csv")
    # Map the simulated export's Action column via profile, not application-specific code.
    # This mapping is included in the checked-in profile.
    x=normalize_rows(p,"warehouse_export",rows)
    assert x["status"]=="NORMALIZED_NOT_RECONCILED"
    assert [(r["product_code"],r["quantity"],r["operation_type"],r["source_row"]) for r in x["rows"]]==[
        ("SYN-101","-12.50","DELIVERY",1),("SYN-102","8.00","RECEIPT",2)]
    assert all(r["warehouse"]=="MAIN" for r in x["rows"])

def test_demo_b_end_to_end_normalization():
    p, rows=fixture("demo_b_3pl_excel.json","demo_b_3pl.csv")
    x=normalize_rows(p,"third_party_log",rows)
    assert x["status"]=="NORMALIZED_NOT_RECONCILED"
    assert [(r["quantity"],r["operation_type"],r["source_row"]) for r in x["rows"]]==[
        ("-4","DELIVERY",1),("6","RECEIPT",2)]
    assert x["matching_performed"] is False and x["stock_changed"] is False

def test_invalid_row_does_not_shift_source_provenance():
    p, rows=fixture("demo_a_wms_erp.json","demo_a_wms.csv")
    rows[0]["MovedQty"]="not-a-quantity"
    x=normalize_rows(p,"warehouse_export",rows)
    assert x["rejected"]==[{"source_row":1,"reason":"INVALID_QUANTITY"}]
    assert x["rows"][0]["source_row"]==2

def test_unmapped_operation_requires_review():
    p, rows=fixture("demo_a_wms_erp.json","demo_a_wms.csv")
    rows[1]["Action"]="UNKNOWN_EVENT"
    x=normalize_rows(p,"warehouse_export",rows)
    assert x["status"]=="REVIEW"
    assert x["rejected"]==[{"source_row":2,"reason":"UNMAPPED_OPERATION"}]

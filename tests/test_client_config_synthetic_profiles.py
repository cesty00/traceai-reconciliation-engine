"""Synthetic client profiles only; no customer data or inventory writes."""
import json
from pathlib import Path
from traceai_reconciliation.client_config.contract import validate_profile_dict

ROOT = Path(__file__).resolve().parents[1] / "examples" / "client_profiles"

def load(name):
    return validate_profile_dict(json.loads((ROOT / name).read_text(encoding="utf-8")))

def test_both_distinct_synthetic_profiles_validate():
    a = load("demo_a_wms_erp.json")
    b = load("demo_b_3pl_excel.json")
    assert a.profile_id != b.profile_id
    assert {s.kind for s in a.sources} == {"wms", "erp"}
    assert {s.kind for s in b.sources} == {"3pl", "excel"}

def test_client_specific_invoice_policy_is_not_global():
    assert load("demo_a_wms_erp.json").enforce_single_warehouse_invoice is True
    assert load("demo_b_3pl_excel.json").enforce_single_warehouse_invoice is False

def test_different_columns_map_to_same_canonical_fields():
    a=load("demo_a_wms_erp.json")
    b=load("demo_b_3pl_excel.json")
    for profile in (a,b):
        for source in profile.sources:
            assert {"product_code", "quantity", "document", "warehouse"} <= set(source.columns)
    assert a.sources[0].columns["quantity"] != b.sources[0].columns["quantity"]

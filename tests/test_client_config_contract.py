import pytest
from traceai_reconciliation.client_config.contract import validate_profile_dict

def sample():
    return {"profile_id": "synthetic-demo",
        "sources": [
            {"key": "logistics", "kind": "wms", "columns": {"product_code": "SKU", "quantity": "Qty"}},
            {"key": "finance", "kind": "erp", "columns": {"document": "InvoiceID", "quantity": "Count"}}],
        "operation_map": {"SHIPMENT": "DELIVERY", "MOVE": "TRANSFER"},
        "warehouse_aliases": {"MAIN": "WAREHOUSE_A", "SECONDARY": "WAREHOUSE_B"},
        "enforce_single_warehouse_invoice": True}

def test_client_profile_is_system_neutral():
    p = validate_profile_dict(sample())
    assert p.sources[0].kind == "wms"
    assert p.sources[1].kind == "erp"
    assert p.enforce_single_warehouse_invoice

def test_single_warehouse_policy_can_be_disabled():
    data = sample()
    data["enforce_single_warehouse_invoice"] = False
    assert not validate_profile_dict(data).enforce_single_warehouse_invoice

def test_unknown_keys_rejected():
    data = sample()
    data["secret"] = "unexpected"
    with pytest.raises(ValueError):
        validate_profile_dict(data)

def test_duplicate_source_keys_rejected():
    data = sample()
    data["sources"][1]["key"] = "logistics"
    with pytest.raises(ValueError):
        validate_profile_dict(data)

def test_ambiguous_column_mapping_rejected():
    data = sample()
    data["sources"][0]["columns"]["document"] = "SKU"
    with pytest.raises(ValueError):
        validate_profile_dict(data)

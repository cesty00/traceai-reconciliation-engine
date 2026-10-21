"""Synthetic economic event ownership checks."""
import importlib.util
from pathlib import Path
p=Path(__file__).parents[1]/"prototypes/core_uat_03/causal_ownership.py"
spec=importlib.util.spec_from_file_location("owner",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def event(row, effect, document="SYN-00060"):
    return {"system":"WMS","source_sha256":"a"*64,"physical_row":row,
            "event_key":f"SYN-{row}","document":document,"effect":effect}

def test_three_inventory_movements_exact_net():
    result=m.validate_causal_ownership([{"component_id":"INV-01",
        "effect":-86.35,"events":[event(10,-131.75),event(11,-0.25),event(12,45.65)]}])
    assert result["status"]=="OWNERSHIP_VERIFIED"
    assert result["components"][0]["calculated_effect"]==-86.35
    assert result["economic_match_authorized"] is False

def test_one_event_two_components_rejected():
    e=event(10,-5)
    result=m.validate_causal_ownership([
        {"component_id":"INV-01","effect":-5,"events":[e]},
        {"component_id":"OTHER","effect":-5,"events":[e]}])
    assert result["status"]=="REVIEW"
    assert "DOUBLE_COUNTED_EVENT" in result["problems"]

def test_duplicate_same_component_rejected():
    e=event(10,-5)
    result=m.validate_causal_ownership([{"component_id":"INV-01","effect":-10,"events":[e,e]}])
    assert "DUPLICATE_EVENT_WITHIN_COMPONENT" in result["problems"]

def test_document_number_is_not_unique_event_identity():
    result=m.validate_causal_ownership([{"component_id":"INV-01","effect":-3,
        "events":[event(10,-5),event(11,2)]}])
    assert result["status"]=="OWNERSHIP_VERIFIED"

def test_component_sum_mismatch_fails():
    result=m.validate_causal_ownership([{"component_id":"INV-01","effect":-10,
        "events":[event(10,-9)]}])
    assert "COMPONENT_EFFECT_MISMATCH" in result["problems"]

def test_missing_source_row_fails():
    e=event(10,-5);e.pop("physical_row")
    result=m.validate_causal_ownership([{"component_id":"INV-01","effect":-5,"events":[e]}])
    assert "MISSING_EVENT_POINTER" in result["problems"]

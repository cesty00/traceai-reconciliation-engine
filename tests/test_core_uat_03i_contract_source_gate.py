"""Synthetic CORE-UAT-03I end-to-end pointer contract and raw-source proof."""
import hashlib
import importlib.util
from pathlib import Path

path=Path(__file__).parents[1]/"prototypes/core_uat_03/contract_source_gate.py"
spec=importlib.util.spec_from_file_location("uat03i_gate",path)
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def make_pointer(tmp_path):
    source=tmp_path/"synthetic.csv"
    source.write_bytes(b"Document;Cod articol;Cantitate\nSYN-100;SYN-P;-10\n")
    return {"source_type":"WMS_CSV","source_path":str(source),
        "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "physical_row":2,"document_ref":"SYN-100","product_ref":"SYN-P",
        "expected_fields":{"Document":"SYN-100","Cod articol":"SYN-P","Cantitate":"-10"},
        "delimiter":";","encoding":"utf-8-sig",
        "pointer_origin":"RAW_PHYSICAL_COORDINATE"}

def test_full_contract_and_source_verified(tmp_path):
    output=gate.verify_contract_and_source(make_pointer(tmp_path))
    assert output["status"]=="SOURCE_ROW_VERIFIED"
    assert output["economic_match_authorized"] is False
    assert output["adjustment_authorized"] is False

def test_internal_rowid_rejected_even_if_file_valid(tmp_path):
    pointer=make_pointer(tmp_path)
    pointer["pointer_origin"]="SQLITE_ROWID"
    output=gate.verify_contract_and_source(pointer)
    assert output["status"]=="REVIEW"
    assert "UNVERIFIED_POINTER_ORIGIN" in output["violations"]

def test_changed_source_rejected_after_pointer_validation(tmp_path):
    pointer=make_pointer(tmp_path)
    with open(pointer["source_path"],"ab") as f: f.write(b"SYN-200;SYN-P;1\n")
    assert gate.verify_contract_and_source(pointer)["reason"]=="SOURCE_SHA_MISMATCH"

def test_wrong_document_rejected_after_pointer_validation(tmp_path):
    pointer=make_pointer(tmp_path)
    pointer["document_ref"]="SYN-OTHER"
    assert gate.verify_contract_and_source(pointer)["status"]=="REVIEW"

def test_missing_coordinate_rejected_before_source_read(tmp_path):
    pointer=make_pointer(tmp_path)
    del pointer["physical_row"]
    result=gate.verify_contract_and_source(pointer)
    assert result["reason"]=="POINTER_CONTRACT_FAILED"

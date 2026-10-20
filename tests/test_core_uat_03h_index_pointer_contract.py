"""Synthetic index pointer contract tests."""
import importlib.util
from pathlib import Path

p=Path(__file__).parents[1]/"prototypes/core_uat_03/index_pointer_contract.py"
spec=importlib.util.spec_from_file_location("ptr",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def valid():
    return {"source_type":"WMS_CSV","source_path":"synthetic.csv",
        "source_sha256":"a"*64,"physical_row":2,
        "document_ref":"SYN-DOC","product_ref":"SYN-P",
        "expected_fields":{"Document":"SYN-DOC","Cod articol":"SYN-P"},
        "delimiter":";","encoding":"utf-8-sig",
        "pointer_origin":"RAW_PHYSICAL_COORDINATE"}

def test_explicit_pointer_contract_accepted():
    assert m.validate_index_pointer_contract(valid()) == ()

def test_sqlite_rowid_without_original_coordinate_fails():
    p=valid();p["pointer_origin"]="SQLITE_ROWID"
    assert "UNVERIFIED_POINTER_ORIGIN" in m.validate_index_pointer_contract(p)

def test_missing_row_fails():
    p=valid();p.pop("physical_row")
    assert "MISSING_PHYSICAL_ROW" in m.validate_index_pointer_contract(p)

def test_wrong_sha_format_fails():
    p=valid();p["source_sha256"]="test"
    assert "INVALID_SHA256" in m.validate_index_pointer_contract(p)

def test_wme_line_number_not_coordinate():
    p={"source_type":"WME_XLSX","source_path":"synthetic.xlsx",
       "source_sha256":"a"*64,"physical_row":9,
       "document_ref":"SYN-DOC","product_ref":"SYN-P",
       "expected_cells":{"C9":"SYN-DOC","K9":"SYN-P"},
       "worksheet_path":"xl/worksheets/sheet1.xml",
       "document_cell":"C9","product_cell":"K9",
       "pointer_origin":"WME_LINENO"}
    assert "UNVERIFIED_POINTER_ORIGIN" in m.validate_index_pointer_contract(p)

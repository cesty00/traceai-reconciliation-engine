"""Synthetic provenance-to-operator-to-DOCX acceptance; no SQLite integration."""
import hashlib
import importlib.util
from pathlib import Path
from docx import Document

MODULE=Path(__file__).parents[1]/"prototypes/core_uat_03/synthetic_pipeline.py"
spec=importlib.util.spec_from_file_location("uat03g",MODULE)
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)

def test_synthetic_chain_preserves_economic_review(tmp_path):
    source=tmp_path/"wms.csv"
    source.write_bytes(b"Document;Cod articol;Cantitate\nSYN-1;SYN-P;-8\n")
    pointer={"source_type":"WMS_CSV","source_path":str(source),
        "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "physical_row":2,"document_ref":"SYN-1","product_ref":"SYN-P",
        "expected_fields":{"Document":"SYN-1","Cod articol":"SYN-P","Cantitate":"-8"}}
    automatic={"case_id":"SYN-CASE","product_code":"SYN-P",
        "difference":-8.0,"residual":0.0,"operator_status":"REVIEW",
        "economic_verdict":"REVIEW"}
    out=tmp_path/"annex.docx"
    result=pipeline.render_verified_case(pointer,automatic,out)
    assert result["status"]=="SOURCE_ROW_VERIFIED"
    assert result["attribution_status"]=="REVIEW"
    assert not result["economic_match_authorized"]
    text="\n".join(p.text for p in Document(out).paragraphs)
    assert "Atribuire documentara: REVIEW" in text
    assert "Verdict economic - neschimbat" in text
    assert automatic["economic_verdict"]=="REVIEW"

def test_hash_change_does_not_write_report(tmp_path):
    source=tmp_path/"wms.csv"
    source.write_bytes(b"Document;Cod articol\nSYN-1;SYN-P\n")
    pointer={"source_type":"WMS_CSV","source_path":str(source),
        "source_sha256":"0"*64,"physical_row":2,
        "document_ref":"SYN-1","product_ref":"SYN-P",
        "expected_fields":{"Document":"SYN-1","Cod articol":"SYN-P"}}
    result=pipeline.render_verified_case(pointer,
        {"case_id":"SYN","product_code":"SYN-P"},tmp_path/"out.docx")
    assert result["status"]=="REVIEW"
    assert not (tmp_path/"out.docx").exists()

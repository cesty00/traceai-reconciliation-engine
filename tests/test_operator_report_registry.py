import json
from pathlib import Path
from traceai_reconciliation.investigation.operator_report_registry import record_generated_report, list_generated_reports

def test_history_persists_reruns_and_archives_original_bytes(tmp_path: Path):
    out=tmp_path/"live"
    out.mkdir()
    docx=out/"case.docx"
    evidence=out/"case.json"
    summary=out/"self_service_summary.json"
    docx.write_bytes(b"first report")
    evidence.write_text(json.dumps({"investigation":{"product_name":"Etichete","initial_difference":-8620.2,"unit":"BUCATA"},"source_readiness":{"source_hashes":{"wms":"abc"}}}),encoding="utf-8")
    summary.write_text(json.dumps({"case_id":"CASE-SELF-40024","product_code":"40024","period":"2026","verdict":"REVIEW","outputs":{"case_docx":str(docx),"case_json":str(evidence)}}),encoding="utf-8")
    archive=tmp_path/"registry"
    first=record_generated_report(summary,root=archive)
    docx.write_bytes(b"second report")
    second=record_generated_report(summary,root=archive)
    assert first!=second
    history=list_generated_reports(root=archive)
    assert len(history)==2
    assert {Path(row["docx_path"]).read_bytes() for row in history}=={b"first report",b"second report"}
    assert all(row["engine_verdict"]=="REVIEW" for row in history)
    assert history[0]["difference"]==-8620.2
    assert list_generated_reports(root=archive)[0]["run_id"]==history[0]["run_id"]

def test_incomplete_report_not_registered(tmp_path: Path):
    import pytest
    summary=tmp_path/"summary.json"
    summary.write_text(json.dumps({"case_id":"X","product_code":"40024","period":"2026","outputs":{"case_docx":"missing.docx","case_json":"missing.json"}}))
    with pytest.raises(FileNotFoundError):
        record_generated_report(summary,root=tmp_path/"registry")
    assert list_generated_reports(root=tmp_path/"registry")==[]


def test_archived_filenames_include_product_and_verification_id(tmp_path):
    from traceai_reconciliation.investigation.operator_report_registry import report_filename
    out=tmp_path/"source"
    out.mkdir()
    (out/"case.docx").write_bytes(b"document")
    (out/"case.json").write_text(json.dumps({"investigation":{"initial_difference":0}}))
    summary=out/"summary.json"
    summary.write_text(json.dumps({"case_id":"CASE-SELF-40024","product_code":"40024","period":"2026","verdict":"REVIEW","outputs":{"case_docx":str(out/"case.docx"),"case_json":str(out/"case.json")}}))
    run_id=record_generated_report(summary,root=tmp_path/"registry")
    row=list_generated_reports(root=tmp_path/"registry")[0]
    assert Path(row["docx_path"]).name==report_filename("40024",run_id,"docx")
    assert Path(row["json_path"]).name==report_filename("40024",run_id,"json")
    assert Path(row["docx_path"]).read_bytes()==b"document"
    assert Path(row["json_path"]).exists()

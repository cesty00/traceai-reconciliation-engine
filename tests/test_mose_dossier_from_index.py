from traceai_reconciliation.mose_control.dossier_from_index import dossier_from_current_index

def test_missing_sources_fail_closed(tmp_path):
    result = dossier_from_current_index(
        case={"case_id": "MOSE-A", "evidence_source_rows": [71944]},
        cache_dir=tmp_path, wms_path=tmp_path/"wms.csv",
        wme_path=tmp_path/"wme.xlsx", production_path=tmp_path/"prod.xlsx")
    assert result["status"] == "SOURCE_FILES_MISSING"
    assert result["verdict"] == "REVIEW"

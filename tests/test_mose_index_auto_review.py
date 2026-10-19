from traceai_reconciliation.mose_control.index_auto_review import create_review_cases_from_existing_index

def test_missing_index_is_not_reported_as_clean_or_matched(tmp_path):
    result = create_review_cases_from_existing_index(
        cache_dir=tmp_path, wms_path=tmp_path/"wms.csv",
        wme_path=tmp_path/"wme.xlsx", production_path=tmp_path/"prod.xlsx")
    assert result["status"] == "SOURCE_INDEX_MISSING_OR_STALE"
    assert result["verdict"] == "REVIEW"
    assert result["cases"] == []

def test_invalid_scan_limit_is_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        create_review_cases_from_existing_index(
            cache_dir=tmp_path, wms_path="wms.csv",
            wme_path="wme.xlsx", production_path="prod.xlsx", max_invoices=0)

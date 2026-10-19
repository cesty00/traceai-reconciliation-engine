from traceai_reconciliation.mose_control.mose_source_index import MOSESQLiteSourceIndex

def test_mose_index_is_independent_of_production(tmp_path):
    idx = MOSESQLiteSourceIndex(tmp_path)
    assert idx.db_path.name == "mose_operational_sources.sqlite"
    assert not idx.is_mose_current(tmp_path/"missing.csv", tmp_path/"missing.xlsx")

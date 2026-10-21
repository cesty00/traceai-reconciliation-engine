"""Document zero-padding must survive both WMS CSV reader paths."""
import pandas as pd
from traceai_reconciliation.investigation.source_index import _csv_chunks, SQLiteSourceIndex
from traceai_reconciliation.investigation.source_readers import filter_csv_by_values

def test_index_wms_import_preserves_document_leading_zeros(tmp_path):
    p=tmp_path/"wms.csv"
    p.write_text("Cod articol;Document intrare;Cantitate\nSYN-P;00060;-5\n",encoding="utf-8")
    data=pd.concat(list(_csv_chunks(p)),ignore_index=True)
    assert data.loc[0,"Document intrare"]=="00060"
    assert SQLiteSourceIndex(tmp_path/"cache").db_path.name=="operational_sources_v2.sqlite"

def test_direct_wms_filter_preserves_document_leading_zeros(tmp_path):
    p=tmp_path/"wms.csv"
    p.write_text("Cod articol;Document intrare;Cantitate\nSYN-P;00060;-5\n",encoding="utf-8")
    data=filter_csv_by_values(p,"product_code",["SYN-P"])
    assert data.iloc[0]["Document intrare"]=="00060"

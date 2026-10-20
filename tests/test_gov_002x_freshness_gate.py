"""GOV-002X test-only freshness and ambiguity gate; no CORE runtime change."""
from __future__ import annotations

import hashlib
import pandas as pd

from test_gov_002w_provenance_probe import _sources, probe_receipt_rows, ProbeResult


def checked_probe(index, wms, wme, production, wms_rows, wme_rows, document, expected_sha):
    """Experimental gate: reject stale source *before* probing candidate rows."""
    if not index.is_current(wms, wme, production):
        return ProbeResult("UNAVAILABLE", (), "STALE_SOURCE_INDEX")
    current = {"WMS": hashlib.sha256(wms.read_bytes()).hexdigest(),
               "WME": hashlib.sha256(wme.read_bytes()).hexdigest()}
    if current != expected_sha:
        return ProbeResult("UNAVAILABLE", (), "SOURCE_HASH_MISMATCH")
    return probe_receipt_rows(wms_rows, wme_rows, document, current)


def test_gov_002x_valid_index_allows_candidate_provenance(tmp_path):
    wms,wme,production,index,wms_rows,wme_rows,sha=_sources(tmp_path)
    result=checked_probe(index,wms,wme,production,wms_rows,wme_rows,"F88",sha)
    assert result.status=="COMPLETE" and len(result.source_lines)==4


def test_gov_002x_stale_wms_rejected_inside_boundary(tmp_path):
    wms,wme,production,index,wms_rows,wme_rows,sha=_sources(tmp_path)
    wms.write_text(wms.read_text(encoding="utf-8").replace("6.0","7.0"),encoding="utf-8")
    result=checked_probe(index,wms,wme,production,wms_rows,wme_rows,"F88",sha)
    assert result == ProbeResult("UNAVAILABLE", (), "STALE_SOURCE_INDEX")


def test_gov_002x_stale_wme_rejected_inside_boundary(tmp_path):
    wms,wme,production,index,wms_rows,wme_rows,sha=_sources(tmp_path)
    from openpyxl import load_workbook
    wb=load_workbook(wme)
    wb.active["E3"]=7
    wb.save(wme)
    result=checked_probe(index,wms,wme,production,wms_rows,wme_rows,"F88",sha)
    assert result.status=="UNAVAILABLE" and not result.source_lines


def test_gov_002x_missing_and_ambiguous_document_fails_closed(tmp_path):
    wms,wme,production,index,wms_rows,wme_rows,sha=_sources(tmp_path)
    missing=checked_probe(index,wms,wme,production,wms_rows,wme_rows,"MISSING",sha)
    assert missing.status=="UNAVAILABLE"
    # A reused WME FE document row from another product must not be
    # mistaken for the same source product merely because document and qty match.
    ambiguous=pd.concat([wme_rows, wme_rows.iloc[[0]].assign(
        ProductName="OTHER PRODUCT", SourceRowNumber=999)],ignore_index=True)
    result=checked_probe(index,wms,wme,production,wms_rows,ambiguous,"F88",sha)
    # Document aggregates cannot prove product-unique ownership in this case.
    assert result.status=="UNAVAILABLE"

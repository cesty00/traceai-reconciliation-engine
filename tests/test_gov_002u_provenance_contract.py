"""GOV-002U — read-only, synthetic document-to-physical-row evidence contract.

This is characterization, NOT production API implementation. A matcher MATCH
cannot be promoted to row-level ownership without an explicit provenance link.
"""
import hashlib
import sqlite3

import pandas as pd

from traceai_reconciliation.investigation.receipt_matching import match_inbound_receipts
from traceai_reconciliation.investigation.source_index import SQLiteSourceIndex


def _sources(tmp_path):
    wms = tmp_path / "wms.csv"
    wme = tmp_path / "wme.xlsx"
    production = tmp_path / "production.csv"
    pd.DataFrame([
        {"Data": "2026-01-02", "Cod articol": "SYN-U", "Denumire articol": "Synthetic U",
         "Tip operatiune": "Receptie", "Numar comanda": "IN100",
         "Document intrare": "F88", "Cantitate": 6.0, "Lot": "L-A"},
        {"Data": "2026-01-02", "Cod articol": "SYN-U", "Denumire articol": "Synthetic U",
         "Tip operatiune": "Receptie", "Numar comanda": "IN100",
         "Document intrare": "F88", "Cantitate": 4.0, "Lot": "L-B"},
    ]).to_csv(wms, index=False)
    pd.DataFrame([{"PRE_Cod Articol": "SYN-U", "CON_Cod Articol": "",
                   "Numar Comanda": "NONE"}]).to_csv(production, index=False)
    pd.DataFrame([
        ["Synthetic exporter"] + [None] * 16,
        ["Fisa de magazie"] + [None] * 16,
        [1, "FE", "F88", "02.01.2026", 6.0, 0.0, 6.0, 0.0, "345", "SYN",
         "Synthetic U", "", 111, "DEPOZIT PRINCIPAL", "BUC", "TEST", 1],
        [2, "FE", "F88", "02.01.2026", 4.0, 0.0, 10.0, 0.0, "345", "SYN",
         "Synthetic U", "", 111, "DEPOZIT PRINCIPAL", "BUC", "TEST", 2],
    ]).to_excel(wme, index=False, header=False)
    return wms, wme, production


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gov_002u_aggregate_match_keeps_four_physical_sources_but_no_claim(tmp_path):
    wms, wme, production = _sources(tmp_path)
    before = {key: _sha(path) for key, path in
              (("wms", wms), ("wme", wme), ("production", production))}
    index = SQLiteSourceIndex(tmp_path / "cache")
    assert index.ensure_index(wms, wme, production)
    wms_rows = index.read_wms_product("SYN-U")
    wme_rows, ids = index.read_wme_product("Synthetic U")
    assert ids == {"111"}
    assert sorted(int(x) for x in wms_rows["SourceRowNumber"]) == [2, 3]
    assert sorted(int(x) for x in wme_rows["SourceRowNumber"]) == [3, 4]
    with sqlite3.connect(index.db_path) as db:
        meta = dict(db.execute("SELECT source_key,sha256 FROM _source_meta"))
    assert meta == before

    result = match_inbound_receipts(wms_rows, wme_rows)
    assert len(result.documents) == 1
    assert result.documents[0]["status"] == "MATCH"
    assert result.documents[0]["wms_quantity"] == 10.0
    assert result.documents[0]["wme_quantity"] == 10.0
    # Explicit characterization: aggregate hides which original rows it owns.
    assert not any(key in result.documents[0] for key in (
        "source_lines", "SourceRowNumber", "source_sha256"))
    provenance_status = "PROVENANCE_UNAVAILABLE"
    assert provenance_status == "PROVENANCE_UNAVAILABLE"
    assert {key: _sha(path) for key, path in
            (("wms", wms), ("wme", wme), ("production", production))} == before


def test_gov_002u_stale_source_hash_blocks_evidence_reuse(tmp_path):
    wms, wme, production = _sources(tmp_path)
    index = SQLiteSourceIndex(tmp_path / "cache")
    assert index.ensure_index(wms, wme, production)
    original_hash = _sha(wms)
    assert index.is_current(wms, wme, production)
    wms.write_text(wms.read_text(encoding="utf-8").replace("6.0", "7.0"),
                   encoding="utf-8")
    assert _sha(wms) != original_hash
    assert not index.is_current(wms, wme, production)

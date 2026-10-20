"""GOV-002R: synthetic physical source coordinates vs document matcher output.

No production code changes; unavailable provenance is recorded, not invented.
"""
import hashlib
import sqlite3

import pandas as pd

from traceai_reconciliation.investigation.source_index import SQLiteSourceIndex
from traceai_reconciliation.investigation.receipt_matching import match_inbound_receipts


def test_gov_002r_index_provenance_does_not_automatically_survive_document_aggregation(tmp_path):
    wms = tmp_path / "wms.csv"
    wme = tmp_path / "wme.xlsx"
    production = tmp_path / "production.csv"
    pd.DataFrame([{
        "Data": "2026-01-02", "Cod articol": "SYN-R",
        "Denumire articol": "Synthetic R", "Tip operatiune": "Receptie",
        "Numar comanda": "IN100", "Document intrare": "F88",
        "Cantitate": 10.0, "Lot": "SYN-L1",
    }]).to_csv(wms, index=False)
    pd.DataFrame([{
        "PRE_Cod Articol": "SYN-R", "CON_Cod Articol": "",
        "Numar Comanda": "NONE",
    }]).to_csv(production, index=False)
    pd.DataFrame([
        ["Synthetic exporter"] + [None] * 16,
        ["Fisa de magazie"] + [None] * 16,
        [1, "FE", "F88", "02.01.2026", 10.0, 0.0, 10.0, 0.0,
         "345", "SYN", "Synthetic R", "", 111,
         "DEPOZIT PRINCIPAL", "BUC", "SYNTHETIC", 1],
    ]).to_excel(wme, index=False, header=False)

    originals = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (wms, wme, production)}
    index = SQLiteSourceIndex(tmp_path / "cache")
    assert index.ensure_index(wms, wme, production)
    wms_rows = index.read_wms_product("SYN-R")
    wme_rows, ids = index.read_wme_product("Synthetic R")
    assert len(wms_rows) == len(wme_rows) == 1
    assert ids == {"111"}
    assert int(wms_rows.iloc[0]["SourceRowNumber"]) == 2
    assert int(wme_rows.iloc[0]["SourceRowNumber"]) == 3
    with sqlite3.connect(index.db_path) as db:
        metadata = dict(db.execute("SELECT source_key, sha256 FROM _source_meta"))
    for key, path in (("wms", wms), ("wme", wme), ("production", production)):
        assert metadata[key] == originals[path.name]

    receipt = match_inbound_receipts(wms_rows, wme_rows)
    assert len(receipt.documents) == 1
    assert receipt.documents[0]["status"] == "MATCH"
    assert receipt.documents[0]["wms_quantity"] == 10.0
    assert receipt.documents[0]["wme_quantity"] == 10.0
    # The aggregate document does not contain a physical-row source claim.
    for field in ("SourceRowNumber", "source_sha256", "source_lines"):
        assert field not in receipt.documents[0], "Unexpected new provenance contract: review explicitly"
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (wms, wme, production)} == originals

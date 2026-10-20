"""GOV-002W: TEST-ONLY prototype of proposed provenance contract.

No CORE implementation, no automatic economic ownership/MATCH authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

import pandas as pd

from traceai_reconciliation.investigation.receipt_matching import match_inbound_receipts
from traceai_reconciliation.investigation.source_index import SQLiteSourceIndex


@dataclass(frozen=True)
class ProbeResult:
    status: str
    source_lines: tuple[tuple[str, str, int], ...]
    reason: str


def probe_receipt_rows(wms_rows, wme_rows, match_document, sha_by_system):
    """Prototype: accept only a fully resolved, unambiguous row set.

    This proof is deliberately conservative and is not a CORE adapter API.
    """
    if not all(len(sha_by_system.get(k, "")) == 64 for k in ("WMS", "WME")):
        return ProbeResult("UNAVAILABLE", (), "SOURCE_HASH_MISSING")
    required_wms = {"SourceRowNumber", "Document intrare", "Cantitate"}
    required_wme = {"SourceRowNumber", "Document", "OperationType", "SignedQuantity"}
    if not required_wms.issubset(wms_rows.columns) or not required_wme.issubset(wme_rows.columns):
        return ProbeResult("UNAVAILABLE", (), "SOURCE_COORDINATES_MISSING")
    wms = wms_rows[wms_rows["Document intrare"].astype(str).eq(match_document)]
    wme = wme_rows[(wme_rows["Document"].astype(str).eq(match_document))
                   & wme_rows["OperationType"].astype(str).eq("FE")]
    if wms.empty or wme.empty:
        return ProbeResult("UNAVAILABLE", (), "SOURCE_SET_INCOMPLETE")
    identities = []
    for system, rows in (("WMS", wms), ("WME", wme)):
        for number in rows["SourceRowNumber"]:
            try:
                line = int(number)
            except (ValueError, TypeError):
                return ProbeResult("UNAVAILABLE", (), "SOURCE_COORDINATES_INVALID")
            if line < 2 or float(number) != line:
                return ProbeResult("UNAVAILABLE", (), "SOURCE_COORDINATES_INVALID")
            identities.append((system, sha_by_system[system], line))
    if len(set(identities)) != len(identities):
        return ProbeResult("UNAVAILABLE", (), "DUPLICATE_SOURCE_IDENTITY")
    wms_qty = pd.to_numeric(wms["Cantitate"], errors="coerce")
    wme_qty = pd.to_numeric(wme["SignedQuantity"], errors="coerce")
    if wms_qty.isna().any() or wme_qty.isna().any() or abs(wms_qty.sum()-wme_qty.sum()) > 0.001:
        return ProbeResult("UNAVAILABLE", (), "QUANTITY_UNVERIFIED")
    return ProbeResult("COMPLETE", tuple(sorted(identities)), "ROW_SET_VERIFIED")


def _sources(tmp_path):
    wms = tmp_path / "wms.csv"
    wme = tmp_path / "wme.xlsx"
    production = tmp_path / "production.csv"
    pd.DataFrame([
        {"Cod articol": "SYN-W", "Denumire articol": "Synthetic W",
         "Data": "2026-01-02", "Tip operatiune": "Receptie",
         "Numar comanda": "IN100", "Document intrare": "F88", "Cantitate": 6.0},
        {"Cod articol": "SYN-W", "Denumire articol": "Synthetic W",
         "Data": "2026-01-02", "Tip operatiune": "Receptie",
         "Numar comanda": "IN100", "Document intrare": "F88", "Cantitate": 4.0},
    ]).to_csv(wms, index=False)
    pd.DataFrame([{"PRE_Cod Articol": "SYN-W", "CON_Cod Articol": ""}]).to_csv(production,index=False)
    pd.DataFrame([
        ["Synthetic exporter"] + [None]*16,
        ["Fisa de magazie"] + [None]*16,
        [1,"FE","F88","02.01.2026",6.0,0.0,6.0,0.0,"345","SYN","Synthetic W","",111,"DP","BUC","TEST",1],
        [2,"FE","F88","02.01.2026",4.0,0.0,10.0,0.0,"345","SYN","Synthetic W","",111,"DP","BUC","TEST",2],
    ]).to_excel(wme,index=False,header=False)
    index=SQLiteSourceIndex(tmp_path/"cache")
    index.ensure_index(wms,wme,production)
    rows_wms=index.read_wms_product("SYN-W")
    rows_wme,_=index.read_wme_product("Synthetic W")
    hashes={"WMS":hashlib.sha256(wms.read_bytes()).hexdigest(),
            "WME":hashlib.sha256(wme.read_bytes()).hexdigest()}
    return wms,wme,production,index,rows_wms,rows_wme,hashes


def test_gov_002w_complete_four_row_source_set_is_not_automatic_ownership(tmp_path):
    wms,wme,production,index,wms_rows,wme_rows,hashes=_sources(tmp_path)
    matched=match_inbound_receipts(wms_rows,wme_rows)
    assert matched.documents[0]["status"]=="MATCH"
    evidence=probe_receipt_rows(wms_rows,wme_rows,"F88",hashes)
    assert evidence.status=="COMPLETE"
    assert {(system,row) for system,_,row in evidence.source_lines}=={
        ("WMS",2),("WMS",3),("WME",3),("WME",4)}
    assert len(evidence.source_lines)==4
    # COMPLETE is physical candidate provenance, never confirmed economic impact.


def test_gov_002w_missing_coordinates_fail_closed(tmp_path):
    _,_,_,_,wms_rows,wme_rows,hashes=_sources(tmp_path)
    assert probe_receipt_rows(wms_rows.drop(columns=["SourceRowNumber"]),wme_rows,"F88",hashes).status=="UNAVAILABLE"


def test_gov_002w_duplicate_source_coordinates_fail_closed(tmp_path):
    _,_,_,_,wms_rows,wme_rows,hashes=_sources(tmp_path)
    wme_rows=wme_rows.copy()
    wme_rows.loc[wme_rows.index[1],"SourceRowNumber"]=wme_rows.iloc[0]["SourceRowNumber"]
    p=probe_receipt_rows(wms_rows,wme_rows,"F88",hashes)
    assert p.status=="UNAVAILABLE" and p.reason=="DUPLICATE_SOURCE_IDENTITY"


def test_gov_002w_modified_source_invalidates_prior_candidate_evidence(tmp_path):
    wms,wme,production,index,wms_rows,wme_rows,hashes=_sources(tmp_path)
    old=probe_receipt_rows(wms_rows,wme_rows,"F88",hashes)
    assert old.status=="COMPLETE"
    wms.write_text(wms.read_text(encoding="utf-8").replace("6.0","7.0"),encoding="utf-8")
    assert not index.is_current(wms,wme,production)
    assert hashlib.sha256(wms.read_bytes()).hexdigest()!=hashes["WMS"]
    # The caller must reject old source evidence when the indexed source is stale.

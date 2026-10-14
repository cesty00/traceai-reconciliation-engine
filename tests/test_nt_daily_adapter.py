from types import SimpleNamespace
from traceai_reconciliation.investigation.nt_daily_adapter import analyze_nt_candidates_in_window


def test_daily_nt_candidate_diagnostic_remains_review():
    window=SimpleNamespace(
        product_code="50005",
        wms_rows=({"Data":"2026-03-21 10:00:00","Tip operatiune":"Mutare intre gestiuni",
                   "Numar comanda":"M8__03C19521","Cantitate":96000,
                   "Locatie sursa":"DEPAMBF","Locatie destinatie":"DEPAMB"},),
        wme_rows=(
            {"Date":"2026-03-21","OperationType":"NT","Document":"19462",
             "Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":-96000},
            {"Date":"2026-03-21","OperationType":"NT","Document":"19462",
             "Warehouse":"SECTIE PRODUCTIE","SignedQuantity":96000},
        ),
    )
    result=analyze_nt_candidates_in_window(window)
    assert result["status"]=="REVIEW"
    assert result["scope_verified"] is False
    assert result["candidates"][0]["nt_document"]=="19462"


def test_competing_wms_moves_cannot_reuse_same_nt():
    window=SimpleNamespace(
        product_code="50005",
        wms_rows=tuple(
            {"Data":"2026-03-21","Tip operatiune":"Mutare intre gestiuni",
             "Numar comanda":doc,"Cantitate":96000,
             "Locatie sursa":"DEPAMBF","Locatie destinatie":"DEPAMB"}
            for doc in ("M8__A","M8__B")
        ),
        wme_rows=(
            {"Date":"2026-03-21","OperationType":"NT","Document":"19462",
             "Warehouse":"DEPOZIT PRINCIPAL","SignedQuantity":-96000},
            {"Date":"2026-03-21","OperationType":"NT","Document":"19462",
             "Warehouse":"SECTIE PRODUCTIE","SignedQuantity":96000},
        ),
    )
    result=analyze_nt_candidates_in_window(window)
    assert all(item["nt_document"] is None for item in result["candidates"])
    assert all(item["reason"]=="SHARED_NT_CANDIDATE" for item in result["candidates"])

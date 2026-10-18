import pandas as pd
from traceai_reconciliation.investigation.operation_timeline import timeline_from_wms

def test_explicit_metadata_is_preserved():
    df = pd.DataFrame([{
        "Data":"2026-10-02", "Document":"SFA24774-1",
        "TipOperatie":"Receptie", "Cantitate":300,
        "Gestiune":"Depozit Principal", "SourceRowNumber":75956,
        "NIR":"NIR06799", "Palet":268045, "Lot":"LOT-A",
        "Locatie":"REC100",
    }])
    row = timeline_from_wms(df)[0]
    assert row["source_row"] == 75956
    assert row["source_metadata"] == {
        "nir":"NIR06799", "pallet":"268045", "lot":"LOT-A", "location":"REC100"
    }

def test_no_guessing_when_metadata_unavailable_or_ambiguous():
    df = pd.DataFrame([{
        "Data":"2026-10-02", "Document":"SFA24774-1",
        "TipOperatie":"Receptie", "Cantitate":300,
        "Gestiune":"Depozit Principal", "Palet":"268045",
        "Cod palet":"DIFFERENT",
    }])
    row = timeline_from_wms(df)[0]
    assert "source_metadata" not in row

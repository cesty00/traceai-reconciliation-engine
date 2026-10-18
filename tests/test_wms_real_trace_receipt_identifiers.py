import pandas as pd
from traceai_reconciliation.investigation.operation_timeline import timeline_from_wms

def test_real_export_receipt_destination_identifiers():
    frame = pd.DataFrame([{
        "Data":"10/2/2026 2:29:24 PM", "Cod articol":"DS056405133",
        "Numar comanda":"SFA24774-1", "Tip operatiune":"Receptie",
        "Cantitate":300, "Depozit":"Depozit Principal",
        "Document comanda":"NIR06799", "Palet destinatie":"268045",
        "Locatie destinatie":"REC100", "Lot":"6042047601",
        "SourceRowNumber":75956,
    }])
    entry = timeline_from_wms(frame)[0]
    assert entry["source_metadata"] == {
        "nir":"NIR06799", "pallet":"268045", "lot":"6042047601", "location":"REC100"
    }
    assert entry["source_row"] == 75956

def test_delivery_does_not_borrow_destination_receipt_fields():
    frame = pd.DataFrame([{
        "Numar comanda":"SFA24774", "Tip operatiune":"Livrare",
        "Cantitate":-900, "Palet sursa":"182783",
        "Locatie sursa":"R02.02.B.3", "Palet destinatie":"182783",
        "Locatie destinatie":"VER100", "Document comanda":"51229",
    }])
    entry = timeline_from_wms(frame)[0]
    assert "nir" not in entry.get("source_metadata", {})
    assert "location" not in entry.get("source_metadata", {})

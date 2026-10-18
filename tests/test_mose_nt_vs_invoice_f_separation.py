from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.transfer_mose_matching import match_transfer_mose


def test_transfer_mose_nt_matches_once_and_f_invoice_does_not_change_match():
    wms = pd.DataFrame([{
        "Data": "05/08/2026 15:55:12",
        "Tip operatiune": "Livrare",
        "Cantitate": -24.0,
        "Numar comanda": "TRANSFER_MOSE-TEST01",
        "Document intrare": None,
        "Document comanda": "TRANSFER_MOSE-TEST01",
    }])
    nt = [
        {"Date": "05.08.2026", "OperationType": "NT",
         "Document": "74626", "SignedQuantity": -24.0,
         "Warehouse": "DEPOZIT PRINCIPAL", "Partner": "MOSE"},
        {"Date": "05.08.2026", "OperationType": "NT",
         "Document": "74626", "SignedQuantity": 24.0,
         "Warehouse": "MOSE", "Partner": "DEPOZIT PRINCIPAL"},
    ]
    invoices = [
        {"Date": "05.08.2026", "OperationType": "F",
         "Document": "94371", "SignedQuantity": -20.0,
         "Warehouse": "MOSE", "Partner": "CLIENT A"},
        {"Date": "05.08.2026", "OperationType": "F",
         "Document": "94377", "SignedQuantity": -4.0,
         "Warehouse": "MOSE", "Partner": "CLIENT B"},
    ]
    without_invoices = match_transfer_mose(wms, pd.DataFrame(nt))
    with_invoices = match_transfer_mose(wms, pd.DataFrame(nt + invoices))
    assert len(with_invoices.matches) == 1
    assert with_invoices.matches == without_invoices.matches
    assert with_invoices.matches[0]["wme_document"] == "74626"
    assert with_invoices.matches[0]["wms_quantity"] == -24.0
    assert with_invoices.matched_wms_total == -24.0
    assert with_invoices.residual_wms_transfers == []
    assert with_invoices.wme_only_nt == []


def test_invoice_f_alone_cannot_replace_missing_nt():
    wms = pd.DataFrame([{
        "Data": "05/08/2026 15:55:12",
        "Tip operatiune": "Livrare",
        "Cantitate": -24.0,
        "Numar comanda": "TRANSFER_MOSE-TEST01",
        "Document intrare": None,
        "Document comanda": "TRANSFER_MOSE-TEST01",
    }])
    f_only = pd.DataFrame([{
        "Date": "05.08.2026", "OperationType": "F",
        "Document": "94371", "SignedQuantity": -24.0,
        "Warehouse": "MOSE", "Partner": "CLIENT A",
    }])
    result = match_transfer_mose(wms, f_only)
    assert result.matches == []
    assert len(result.residual_wms_transfers) == 1
    assert result.residual_wms_transfers[0]["status"] == "NO_NT_MATCH_REVIEW"

"""Regression: internal MOSE transfer is not a customer delivery."""
import sqlite3

from traceai_reconciliation.mose_control.wms_candidate_index import screen_wms_invoice_candidates
from traceai_reconciliation.mose_control.invoice_balance_evidence import invoice_balance_evidence


def test_f91655_transfer_separate_from_customer_delivery(tmp_path):
    index = tmp_path / "index.sqlite"
    with sqlite3.connect(index) as db:
        db.execute(
            'CREATE TABLE wms ("Denumire articol" TEXT, "Tip operatiune" TEXT, '
            '"Numar comanda" TEXT, "Cantitate" REAL, "Data" TEXT, '
            '"Partener" TEXT, SourceRowNumber INTEGER)'
        )
        db.execute("INSERT INTO wms VALUES (?,?,?,?,?,?,?)", (
            "FILE CRAP CU PIELE 300-500G, BAX 10KG VRAC", "Livrare",
            "TRANSFER_MOSE-202520832", -10, "3/11/2026 12:25:11 PM",
            "DP->MOSE", 100))
    result = screen_wms_invoice_candidates(
        index, ["FILE CRAP CU PIELE 300-500G, BAX 10KG VRAC"],
        invoice_date="2026-03-11", invoice_partner="FISHERMEN INN S.R.L.")
    assert result["status"] == "WMS_CANDIDATES_REVIEW"
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["candidate_class"] == "TRANSFER_MOSE"
    assert result["candidates"][0]["partner_screen"] == "NOT_APPLICABLE_TRANSFER"


def test_f91655_two_stock_outflows_do_not_confirm_error():
    evidence = invoice_balance_evidence([
        {"warehouse": "DEPOZIT PRINCIPAL", "unit": "KG", "source_row": 71944,
         "quantity": -10, "reported_balance": 6560},
        {"warehouse": "MOSE", "unit": "KG", "source_row": 72103,
         "quantity": -10, "reported_balance": 0},
    ])
    assert evidence["verdict"] == "REVIEW"
    assert len(evidence["records"]) == 2

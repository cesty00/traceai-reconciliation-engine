import sqlite3
from traceai_reconciliation.mose_control.wms_candidate_index import screen_wms_invoice_candidates


def make_db(path):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE wms ("Denumire articol" TEXT, "Tip operatiune" TEXT, "Numar comanda" TEXT, "Cantitate" REAL, "Data" TEXT, SourceRowNumber INTEGER)')
        db.executemany("INSERT INTO wms VALUES (?,?,?,?,?,?)", [
            ("FILE CRAP", "Livrare", "TRANSFER_MOSE-01", -10, "2026-03-11", 10),
            ("FILE CRAP", "Livrare", "SFA-01", -10, "2026-03-11", 11),
            ("OTHER", "Livrare", "SFA-02", -10, "2026-03-11", 12),
        ])


def test_separates_transfer_and_customer_delivery_without_matching(tmp_path):
    path = tmp_path / "idx.sqlite"
    make_db(path)
    result = screen_wms_invoice_candidates(path, ["FILE CRAP"])
    assert result["status"] == "WMS_CANDIDATES_REVIEW"
    assert {x["candidate_class"] for x in result["candidates"]} == {"TRANSFER_MOSE", "DIRECT_DELIVERY_CANDIDATE"}
    assert result["verdict"] == "REVIEW"


def test_no_product_name_does_not_invent_candidate(tmp_path):
    path = tmp_path / "idx.sqlite"
    make_db(path)
    assert screen_wms_invoice_candidates(path, ["UNKNOWN"])["candidates"] == []


def test_missing_columns_explicitly_block(tmp_path):
    path = tmp_path / "idx.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE wms (SourceRowNumber INTEGER)")
    assert screen_wms_invoice_candidates(path, ["FILE CRAP"])["status"] == "WMS_COLUMNS_UNSUPPORTED_REVIEW"


def test_candidate_limit_reported(tmp_path):
    path = tmp_path / "idx.sqlite"
    make_db(path)
    result = screen_wms_invoice_candidates(path, ["FILE CRAP"], limit_per_product=1)
    assert result["truncated"] is True
    assert len(result["candidates"]) == 1

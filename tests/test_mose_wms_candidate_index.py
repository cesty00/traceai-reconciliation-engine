import sqlite3
from traceai_reconciliation.mose_control.wms_candidate_index import screen_wms_invoice_candidates


def make_db(path):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE wms ("Denumire articol" TEXT, "Tip operatiune" TEXT, "Numar comanda" TEXT, "Cantitate" REAL, "Data" TEXT, "Partener" TEXT, SourceRowNumber INTEGER)')
        db.executemany("INSERT INTO wms VALUES (?,?,?,?,?,?,?)", [
            ("FILE CRAP", "Livrare", "TRANSFER_MOSE-01", -10, "2026-03-11", "DP->MOSE", 10),
            ("FILE CRAP", "Livrare", "SFA-01", -10, "2026-03-11", "FISHERMEN INN S.R.L.-Sediu Firma", 11),
            ("OTHER", "Livrare", "SFA-02", -10, "2026-03-11", "OTHER", 12),
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


def test_invoice_date_filters_future_and_keeps_historical_transfer(tmp_path):
    path = tmp_path / "idx.sqlite"
    make_db(path)
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO wms VALUES (?,?,?,?,?,?,?)',
                   ("FILE CRAP", "Livrare", "FUTURE", -10, "2026-10-07", "OTHER", 13))
    result = screen_wms_invoice_candidates(
        path, ["FILE CRAP"], invoice_date="2026-03-11", lookback_days=30)
    docs = {x["document"] for x in result["candidates"]}
    assert "TRANSFER_MOSE-01" in docs
    assert "FUTURE" not in docs
    assert result["truncated"] is False

def test_us_date_and_customer_partner_screen(tmp_path):
    path = tmp_path / "idx.sqlite"
    make_db(path)
    with sqlite3.connect(path) as db:
        db.execute('UPDATE wms SET "Data"=? WHERE "Numar comanda"=?',
                   ("3/11/2026 12:25:11 PM", "TRANSFER_MOSE-01"))
    result = screen_wms_invoice_candidates(
        path, ["FILE CRAP"], invoice_date="2026-03-11",
        invoice_partner="FISHERMEN INN S.R.L.")
    assert len(result["candidates"]) == 2
    by_doc = {x["document"]: x for x in result["candidates"]}
    assert by_doc["TRANSFER_MOSE-01"]["candidate_class"] == "TRANSFER_MOSE"
    assert by_doc["SFA-01"]["partner_screen"] == "PARTNER_CANDIDATE"

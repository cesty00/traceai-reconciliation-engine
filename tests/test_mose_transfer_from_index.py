import sqlite3
from traceai_reconciliation.mose_control.transfer_from_index import screen_transfer_from_mose_index

def test_full_transfer_document_screen_from_index(tmp_path):
    path = tmp_path / "mose.sqlite"
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE wms ("Numar comanda", "Denumire articol", "Cantitate", SourceRowNumber)')
        db.execute('CREATE TABLE wme (OperationType, Document, ProductName, SignedQuantity, Warehouse, SourceRowNumber)')
        db.executemany('INSERT INTO wms VALUES (?,?,?,?)', [
            ("TRANSFER_MOSE-202520832", "FILE CRAP", -10, 154975),
            ("TRANSFER_MOSE-202520832", "CALAMAR", -65, 154976)])
        db.executemany('INSERT INTO wme VALUES (?,?,?,?,?,?)', [
            ("NT","62513","FILE CRAP",-10,"DEPOZIT PRINCIPAL",71943),
            ("NT","62513","FILE CRAP",10,"MOSE",72102),
            ("NT","62513","CALAMAR",-65,"DEPOZIT PRINCIPAL",71945),
            ("NT","62513","CALAMAR",65,"MOSE",72104)])
    x = screen_transfer_from_mose_index(path, wms_document="TRANSFER_MOSE-202520832", wme_nt="62513")
    assert x["status"] == "TRANSFER_QUANTITIES_EQUAL_UNVERIFIED"
    assert x["article_count"] == 2
    assert x["wms_total"] == x["wme_dp_total"] == x["wme_mose_total"] == 75
    assert x["document_identity"] == "NOT_VERIFIED"
    assert x["verdict"] == "REVIEW"

def test_mixed_warehouse_nt_blocks_not_silently_dropped(tmp_path):
    path = tmp_path / "mose.sqlite"
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE wms ("Numar comanda", "Denumire articol", "Cantitate", SourceRowNumber)')
        db.execute('CREATE TABLE wme (OperationType, Document, ProductName, SignedQuantity, Warehouse, SourceRowNumber)')
        db.execute('INSERT INTO wms VALUES (?,?,?,?)', ("TRANSFER_MOSE-1", "A", -5, 2))
        db.execute('INSERT INTO wme VALUES (?,?,?,?,?,?)', ("NT","99","A",5,"PROD101",3))
    x=screen_transfer_from_mose_index(path,wms_document="TRANSFER_MOSE-1",wme_nt="99")
    assert x["status"] == "TRANSFER_NT_OTHER_WAREHOUSE_OR_SIGN_REVIEW"

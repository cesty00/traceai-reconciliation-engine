"""GOV-AT-01..04: synthetic two-source MOSE index integration and provenance."""
import sqlite3
from pathlib import Path

import pytest
from openpyxl import Workbook

from traceai_reconciliation.mose_control.mose_source_index import MOSESQLiteSourceIndex


def sources(tmp_path):
    wms=tmp_path/"synthetic_wms.csv"
    wms.write_text("Denumire articol,Tip operatiune,Numar comanda,Data,Cantitate,Partener\nFAKE FISH,Livrare,TRANSFER_MOSE-DEMO,2026-10-01,-10,DP->MOSE\n",encoding="utf-8")
    wme=tmp_path/"synthetic_wme.xlsx"
    wb=Workbook()
    sheet=wb.active
    sheet.append(list("ABCDEFGHIJKLMNOPQ"))
    sheet.append([1,"NT","DEMO-NT","2026-10-01",0,10,0,0,"","", "FAKE FISH", "", "SYN-01", "DP", "KG", "MOSE", ""])
    wb.save(wme)
    return wms,wme


def test_gov_at_01_synthetic_sources_keep_physical_rows_and_sha(tmp_path):
    wms,wme=sources(tmp_path)
    raw_wms=wms.read_bytes()
    raw_wme=wme.read_bytes()
    idx=MOSESQLiteSourceIndex(tmp_path/"cache")
    assert idx.ensure_mose_index(wms,wme) is True
    assert wms.read_bytes()==raw_wms and wme.read_bytes()==raw_wme
    assert idx.is_mose_current(wms,wme)
    with sqlite3.connect(idx.db_path) as db:
        assert db.execute("SELECT SourceRowNumber FROM wms").fetchall()==[(2,)]
        assert db.execute("SELECT SourceRowNumber, SignedQuantity FROM wme").fetchall()==[(2,-10.0)]
        metadata=db.execute("SELECT source_key,sha256 FROM _source_meta ORDER BY source_key").fetchall()
        assert [key for key,_ in metadata]==["wme","wms"]
        assert all(len(digest)==64 for _,digest in metadata)


def test_gov_at_02_unchanged_sources_reuse_index(tmp_path):
    wms,wme=sources(tmp_path)
    idx=MOSESQLiteSourceIndex(tmp_path/"cache")
    assert idx.ensure_mose_index(wms,wme) is True
    before=idx.db_path.read_bytes()
    assert idx.ensure_mose_index(wms,wme) is False
    assert idx.db_path.read_bytes()==before


def test_gov_at_03_change_wme_invalidates_cache(tmp_path):
    wms,wme=sources(tmp_path)
    idx=MOSESQLiteSourceIndex(tmp_path/"cache")
    idx.ensure_mose_index(wms,wme)
    wb=Workbook()
    sheet=wb.active
    sheet.append(list("ABCDEFGHIJKLMNOPQ"))
    sheet.append([1,"NT","DEMO-NT","2026-10-01",0,9,0,0,"","", "FAKE FISH", "", "SYN-01", "DP", "KG", "MOSE", ""])
    wb.save(wme)
    assert not idx.is_mose_current(wms,wme)
    assert idx.ensure_mose_index(wms,wme) is True
    with sqlite3.connect(idx.db_path) as db:
        assert db.execute("SELECT SignedQuantity FROM wme").fetchone()[0]==-9


def test_gov_at_04_missing_wms_column_fails_no_index(tmp_path):
    wms,wme=sources(tmp_path)
    wms.write_text("Wrong,Cantitate\nFAKE,-10\n",encoding="utf-8")
    idx=MOSESQLiteSourceIndex(tmp_path/"cache")
    with pytest.raises(ValueError,match="required MOSE columns"):
        idx.ensure_mose_index(wms,wme)
    assert not idx.db_path.exists()

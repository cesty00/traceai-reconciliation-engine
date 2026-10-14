from pathlib import Path
import sqlite3
import pandas as pd
from openpyxl import Workbook
from traceai_reconciliation.investigation.source_index import SQLiteSourceIndex, _csv_chunks


def test_csv_source_row_numbers_survive_chunk_boundaries(tmp_path: Path):
    path=tmp_path/"source.csv"
    path.write_text("Cod articol;Cantitate\n10002;4\n10002;7\n10002;9\n",encoding="utf-8")
    chunks=list(_csv_chunks(path,chunksize=2))
    assert [int(n) for c in chunks for n in c["SourceRowNumber"]]==[2,3,4]
    assert [int(n) for c in chunks for n in c["Cantitate"]]==[4,7,9]


def test_wme_xlsx_physical_source_rows(tmp_path: Path):
    path=tmp_path/"wme.xlsx"
    wb=Workbook()
    ws=wb.active
    ws.append(["header"]*17)
    ws.append([101,"NT","9833","2026-02-18",4950,0,0,0,"","", "CUTIE", "","1494","DEPOZIT PRINCIPAL","BUC","",""])
    ws.append([102,"NT","9833","2026-02-18",0,4950,0,0,"","", "CUTIE", "","1494","SECTIE PRODUCTIE","BUC","",""])
    wb.save(path)
    idx=SQLiteSourceIndex(tmp_path/"cache")
    with sqlite3.connect(":memory:") as connection:
        idx._build_wme(connection,path)
        result=connection.execute("SELECT SourceRowNumber,SignedQuantity FROM wme ORDER BY SourceRowNumber").fetchall()
    assert result==[(2,4950.0),(3,-4950.0)]


def test_csv_physical_lines_with_multiline_and_blank_rows(tmp_path: Path):
    path = tmp_path / "multiline.csv"
    path.write_bytes(
        b'Cod articol;Note;Cantitate\r\n'
        b'10002;"first\r\nsecond";4\r\n'
        b'\r\n'
        b'10002;normal;7\r\n'
    )
    chunks = list(_csv_chunks(path, chunksize=1))
    assert [int(v) for x in chunks for v in x["SourceRowNumber"]] == [2, 5]
    assert [int(v) for x in chunks for v in x["Cantitate"]] == [4, 7]


def test_csv_malformed_row_is_not_indexed_with_false_provenance(tmp_path: Path):
    import pytest
    path = tmp_path / "broken.csv"
    path.write_text("Cod articol;Cantitate\n10002;4\n10002;7;EXTRA\n", encoding="utf-8")
    with pytest.raises(ValueError):
        list(_csv_chunks(path, chunksize=1))


def test_index_end_to_end_provenance_and_cache_reuse(tmp_path: Path):
    """Full index (three sources) retains coordinates and invalidates changed data."""
    wms = tmp_path / "wms.csv"
    wms.write_bytes(
        b'Cod articol;Data;Note\r\n'
        b'10002;2026-02-18;"first\r\nsecond"\r\n'
        b'10002;2026-02-19;normal\r\n'
    )
    production = tmp_path / "production.csv"
    production.write_text(
        "PRE_Cod Articol;CON_Cod Articol\n10002;10002\n",
        encoding="utf-8",
    )
    wme = tmp_path / "wme.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["header"] * 17)
    ws.append([
        101, "NT", "9833", "2026-02-18", 4950, 0, 0, 0,
        "", "", "CUTIE", "", "1494", "DEPOZIT PRINCIPAL",
        "BUC", "", "",
    ])
    wb.save(wme)
    index = SQLiteSourceIndex(tmp_path / "cache")
    assert index.ensure_index(wms, wme, production) is True
    with sqlite3.connect(index.db_path) as con:
        assert con.execute(
            'SELECT SourceRowNumber FROM wms ORDER BY SourceRowNumber'
        ).fetchall() == [(2,), (4,)]
        assert con.execute(
            'SELECT SourceRowNumber,Document,SignedQuantity FROM wme'
        ).fetchall() == [(2, "9833", 4950.0)]
        hashes = dict(con.execute(
            "SELECT source_key,sha256 FROM _source_meta"
        ).fetchall())
        assert len(hashes) == 3
        assert all(len(value) == 64 for value in hashes.values())
    assert index.ensure_index(wms, wme, production) is False

    wms.write_bytes(wms.read_bytes() + b'10002;2026-02-20;updated\r\n')
    assert index.ensure_index(wms, wme, production) is True
    with sqlite3.connect(index.db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM wms").fetchone()[0] == 3

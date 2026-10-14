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

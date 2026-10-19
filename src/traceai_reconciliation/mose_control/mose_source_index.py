"""Independent, content-verified two-source MOSE index.

Reuses canonical WMS provenance and WME XLSX decoding, never asks for production.
"""
from __future__ import annotations
from contextlib import closing
import os
import sqlite3
from pathlib import Path
from traceai_reconciliation.investigation.source_index import SQLiteSourceIndex, _csv_chunks, _fingerprint


class MOSESQLiteSourceIndex(SQLiteSourceIndex):
    def __init__(self, cache_dir):
        super().__init__(cache_dir)
        self.db_path = self.cache_dir / "mose_operational_sources.sqlite"

    def _expected_meta(self, wms_path, wme_path, production_path=None):
        return {"wms": _fingerprint(wms_path), "wme": _fingerprint(wme_path)}

    def _build(self, target, wms_path, wme_path, production_path=None):
        with closing(sqlite3.connect(target)) as db, db:
            first = True
            for chunk in _csv_chunks(Path(wms_path)):
                chunk.to_sql("wms", db, if_exists="replace" if first else "append", index=False)
                first = False
            if first:
                raise ValueError("WMS empty; MOSE index not built")
            self._build_wme(db, Path(wme_path))
            wms_columns = {row[1] for row in db.execute("PRAGMA table_info(wms)")}
            required = {"Denumire articol", "Tip operatiune", "Numar comanda",
                        "Data", "Cantitate", "Partener", "SourceRowNumber"}
            if not required.issubset(wms_columns):
                raise ValueError("WMS required MOSE columns missing")
            db.execute('CREATE INDEX idx_mose_wms_product ON wms("Denumire articol")')
            db.execute('CREATE INDEX idx_mose_wme_document ON wme(OperationType, Document, Date)')
            db.execute('CREATE INDEX idx_mose_wme_product ON wme(ProductName)')
            db.execute("CREATE TABLE _source_meta (source_key TEXT PRIMARY KEY, file_name TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL)")
            db.executemany("INSERT INTO _source_meta VALUES (?,?,?,?)",
                [(key, val["file_name"], val["size"], val["sha256"])
                 for key, val in self._expected_meta(wms_path, wme_path).items()])

    def is_mose_current(self, wms_path, wme_path):
        return self.is_current(wms_path, wme_path, wme_path)

    def ensure_mose_index(self, wms_path, wme_path):
        return self.ensure_index(wms_path, wme_path, wme_path)

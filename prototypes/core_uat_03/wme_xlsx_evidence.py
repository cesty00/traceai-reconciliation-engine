"""Isolated WME XLSX row-coordinate evidence verifier. No CORE integration.

Uses original worksheet XML coordinate and raw file SHA. Rejects ambiguous data.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from lxml import etree

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

def verify_wme_xlsx_evidence(source_path, *, expected_sha256, worksheet_path,
                             physical_row, expected_cells):
    path = Path(source_path)
    if (not path.is_file() or not isinstance(expected_sha256, str) or
        not isinstance(worksheet_path, str) or
        not worksheet_path.startswith("xl/worksheets/") or
        ".." in worksheet_path or
        not isinstance(physical_row, int) or isinstance(physical_row, bool) or
        physical_row < 1 or not isinstance(expected_cells, dict) or
        not expected_cells):
        return {"verified": False, "reason": "INVALID_POINTER"}
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest().lower() != expected_sha256.lower():
        return {"verified": False, "reason": "SOURCE_SHA_MISMATCH"}
    try:
        with ZipFile(path) as archive:
            if worksheet_path not in archive.namelist():
                return {"verified": False, "reason": "WORKSHEET_NOT_FOUND"}
            shared = []
            if "xl/sharedStrings.xml" in archive.namelist():
                with archive.open("xl/sharedStrings.xml") as stream:
                    tree = etree.parse(stream)
                    shared = ["".join(e.itertext()) for e in tree.findall(NS + "si")]
            with archive.open(worksheet_path) as stream:
                row_matches = 0
                for _, row in etree.iterparse(stream, events=("end",), tag=NS + "row"):
                    raw = row.get("r")
                    if raw is not None and raw.isdecimal() and int(raw) == physical_row:
                        row_matches += 1
                        cells = {}
                        for c in row.findall(NS + "c"):
                            ref = c.get("r")
                            if not ref or ref in cells:
                                return {"verified": False, "reason": "AMBIGUOUS_CELL"}
                            typ = c.get("t")
                            v = c.find(NS + "v")
                            value = v.text if v is not None else None
                            if typ == "s" and value is not None:
                                idx = int(value)
                                if idx < 0 or idx >= len(shared):
                                    return {"verified": False, "reason": "SOURCE_PARSE_ERROR"}
                                value = shared[idx]
                            elif typ == "inlineStr":
                                inline = c.find(NS + "is")
                                value = "".join(inline.itertext()) if inline is not None else ""
                            cells[ref] = value
                        if any(cells.get(k) != str(v) for k, v in expected_cells.items()):
                            return {"verified": False, "reason": "DOCUMENT_OR_CELL_MISMATCH"}
                    row.clear()
                    while row.getprevious() is not None:
                        del row.getparent()[0]
                if row_matches != 1:
                    return {"verified": False, "reason": "AMBIGUOUS_OR_MISSING_ROW"}
    except (BadZipFile, OSError, etree.XMLSyntaxError, ValueError, IndexError):
        return {"verified": False, "reason": "SOURCE_PARSE_ERROR"}
    return {"verified": True, "reason": "SOURCE_ROW_VERIFIED",
            "sha256": digest.hexdigest(), "worksheet_path": worksheet_path,
            "physical_row": physical_row}

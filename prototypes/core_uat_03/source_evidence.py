"""CORE-UAT-03C: independent verification of a WMS CSV evidence pointer.

Stand-alone, read-only, exact-byte source SHA and physical CSV line check.
No database, engine, accounting, UI, or WME integration.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Mapping, Any


def verify_wms_csv_evidence(
    source_path: str | Path,
    *,
    expected_sha256: str,
    physical_row: int,
    expected_fields: Mapping[str, Any],
    encoding: str = "utf-8-sig",
    delimiter: str = ";",
) -> dict[str, Any]:
    """Fail closed unless SHA, physical record start and expected field values agree.

    csv.reader.line_num reflects physical lines, including quoted newlines.
    The asserted physical_row must be the record's START line, never a DataFrame index.
    """
    source = Path(source_path)
    if (not source.is_file() or not expected_sha256 or
            not isinstance(physical_row, int) or isinstance(physical_row, bool) or
            physical_row < 2 or not expected_fields):
        return {"verified": False, "reason": "INVALID_POINTER"}
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest().lower() != str(expected_sha256).lower():
        return {"verified": False, "reason": "SOURCE_SHA_MISMATCH"}
    try:
        with source.open("r", encoding=encoding, newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter, strict=True)
            headers = next(reader)
            if len(headers) != len(set(headers)):
                return {"verified": False, "reason": "DUPLICATE_HEADERS"}
            if not set(expected_fields).issubset(headers):
                return {"verified": False, "reason": "MISSING_COLUMNS"}
            prev_line = reader.line_num
            for values in reader:
                start_line = prev_line + 1
                prev_line = reader.line_num
                if start_line != physical_row:
                    continue
                if len(values) != len(headers):
                    return {"verified": False, "reason": "MALFORMED_ROW"}
                actual = dict(zip(headers, values))
                if any(actual[key] != str(value) for key, value in expected_fields.items()):
                    return {"verified": False, "reason": "DOCUMENT_OR_ROW_MISMATCH"}
                return {"verified": True, "reason": "SOURCE_ROW_VERIFIED",
                        "sha256": digest.hexdigest(), "physical_row": start_line}
    except (UnicodeError, csv.Error, OSError, StopIteration):
        return {"verified": False, "reason": "SOURCE_PARSE_ERROR"}
    return {"verified": False, "reason": "ROW_NOT_FOUND"}

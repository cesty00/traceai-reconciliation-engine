"""A verified publication marker for a pair of Daily case artifacts.

The marker is written LAST. Its presence is not sufficient: consumers must
verify both file SHA256 values before trusting the pair as complete.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


MARKER_NAME = "case_publication.json"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def publication_payload(case_id: str, case_json: Path, case_docx: Path) -> dict:
    if not case_id.strip() or not case_json.is_file() or not case_docx.is_file():
        raise ValueError("publication requires case identity and both outputs")
    return {
        "schema_version": "1",
        "case_id": case_id,
        "status": "COMPLETE",
        "files": {
            "case.json": sha256_path(case_json),
            "case.docx": sha256_path(case_docx),
        },
    }


def verify_case_publication(case_dir: str | Path, *, case_id: str) -> bool:
    root = Path(case_dir)
    marker = root / MARKER_NAME
    if not marker.is_file():
        raise ValueError(f"{case_id}: publication manifest missing")
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{case_id}: invalid publication manifest") from exc
    if not isinstance(data, dict) or data.get("schema_version") != "1":
        raise ValueError(f"{case_id}: unsupported publication schema")
    if data.get("status") != "COMPLETE" or data.get("case_id") != case_id:
        raise ValueError(f"{case_id}: incomplete or mismatched publication")
    hashes = data.get("files")
    if not isinstance(hashes, dict) or set(hashes) != {"case.json", "case.docx"}:
        raise ValueError(f"{case_id}: missing publication hashes")
    for name, expected in hashes.items():
        file_path = root / name
        if not file_path.is_file() or not isinstance(expected, str) or len(expected) != 64:
            raise ValueError(f"{case_id}: missing or malformed {name}")
        if sha256_path(file_path) != expected:
            raise ValueError(f"{case_id}: publication hash mismatch for {name}")
    return True

"""Synthetic fail-closed tests for source evidence. No real source files."""
import hashlib
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).parents[1] / "prototypes/core_uat_03/source_evidence.py"
spec = importlib.util.spec_from_file_location("uat03_source_evidence", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample(tmp_path):
    source = tmp_path / "wms.csv"
    source.write_bytes(b"Document;Cod articol;Cantitate\nSYN001;SYN-P;10\nSYN002;SYN-P;-10\n")
    return source, hashlib.sha256(source.read_bytes()).hexdigest()


def test_exact_hash_document_and_physical_line(tmp_path):
    path, sha = sample(tmp_path)
    result = mod.verify_wms_csv_evidence(path, expected_sha256=sha,
        physical_row=3, delimiter=";", expected_fields={"Document": "SYN002", "Cantitate": "-10"})
    assert result["verified"] is True


def test_sha_change_invalidates_original_claim(tmp_path):
    path, sha = sample(tmp_path)
    path.write_bytes(path.read_bytes() + b"SYN003;SYN-P;1\n")
    result = mod.verify_wms_csv_evidence(path, expected_sha256=sha,
        physical_row=3, expected_fields={"Document": "SYN002"})
    assert result == {"verified": False, "reason": "SOURCE_SHA_MISMATCH"}


def test_correct_hash_wrong_document_fails(tmp_path):
    path, sha = sample(tmp_path)
    result = mod.verify_wms_csv_evidence(path, expected_sha256=sha,
        physical_row=3, expected_fields={"Document": "SYN001"})
    assert result["reason"] == "DOCUMENT_OR_ROW_MISMATCH"


def test_missing_row_fails(tmp_path):
    path, sha = sample(tmp_path)
    result = mod.verify_wms_csv_evidence(path, expected_sha256=sha,
        physical_row=999, expected_fields={"Document": "SYN002"})
    assert result["reason"] == "ROW_NOT_FOUND"


def test_multiline_csv_uses_record_start_physical_line(tmp_path):
    path = tmp_path / "multi.csv"
    path.write_bytes(b'Document;Note\nSYN001;"first\nsecond"\nSYN002;end\n')
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    yes = mod.verify_wms_csv_evidence(path, expected_sha256=sha, physical_row=4,
        expected_fields={"Document": "SYN002"})
    no = mod.verify_wms_csv_evidence(path, expected_sha256=sha, physical_row=3,
        expected_fields={"Document": "SYN002"})
    assert yes["verified"] is True
    assert no["verified"] is False


def test_ambiguous_duplicate_headers_rejected(tmp_path):
    path = tmp_path / "dup.csv"
    path.write_bytes(b"Document;Document\nSYN001;SYN002\n")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    result = mod.verify_wms_csv_evidence(path, expected_sha256=sha, physical_row=2,
        expected_fields={"Document": "SYN001"})
    assert result["reason"] == "DUPLICATE_HEADERS"

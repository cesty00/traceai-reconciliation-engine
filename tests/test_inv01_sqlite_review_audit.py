import importlib.util
from pathlib import Path
import sqlite3
import pytest
p=Path(__file__).parents[1]/"prototypes/core_uat_03/sqlite_review_audit.py"
spec=importlib.util.spec_from_file_location("audit",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def writer(tmp_path):
    return m.SQLiteReviewAudit(tmp_path/"review.sqlite")
def decision(w, expected=0, reviewer="TRUSTED-1", authorized=True):
    return w.append(case_id="SYN-CASE",expected_revision=expected,
        trusted_reviewer_id=reviewer,authorized=authorized,
        decision="CONFIRMED",evidence_refs=["SYN-REF"],comment="Synthetic review",
        reviewed_at="2026-10-21T12:00:00+03:00")

def test_persists_and_preserves_review_economics(tmp_path):
    w=writer(tmp_path);r=decision(w)
    assert r["revision"]==1 and r["economic_verdict"]=="REVIEW"
    assert m.SQLiteReviewAudit(w.path).read("SYN-CASE")[0]["decision"]=="CONFIRMED"

def test_rejects_unauthorized_reviewer(tmp_path):
    w=writer(tmp_path)
    with pytest.raises(m.ReviewAccessDenied):decision(w,authorized=False)
    assert w.read("SYN-CASE")==[]

def test_stale_second_reviewer_conflicts(tmp_path):
    w=writer(tmp_path);decision(w)
    with pytest.raises(m.ReviewConflict):decision(w,expected=0,reviewer="TRUSTED-2")
    assert len(w.read("SYN-CASE"))==1

def test_corrections_append_not_overwrite(tmp_path):
    w=writer(tmp_path);first=decision(w)
    second=decision(w,expected=1,reviewer="TRUSTED-2")
    events=w.read("SYN-CASE")
    assert len(events)==2 and events[0]["entry_hash"]==first["entry_hash"]
    assert events[1]["entry_hash"]==second["entry_hash"]

def test_update_and_delete_rejected(tmp_path):
    w=writer(tmp_path);decision(w)
    with sqlite3.connect(w.path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE review_events SET reviewer_id='X' WHERE case_id='SYN-CASE'")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM review_events WHERE case_id='SYN-CASE'")

def test_audit_tampering_detected(tmp_path):
    w=writer(tmp_path);decision(w)
    with sqlite3.connect(w.path) as db:
        db.execute("DROP TRIGGER review_no_update")
        db.execute("UPDATE review_events SET payload='{}'")
    with pytest.raises(ValueError,match="integrity"):
        w.read("SYN-CASE")

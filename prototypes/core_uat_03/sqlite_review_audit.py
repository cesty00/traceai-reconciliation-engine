"""Isolated prototype: persistent append-only documentary review audit.

Not connected to Daily, CORE economics or a real authentication provider.
The caller MUST inject a server-authenticated reviewer identity and
authorization decision; this module does not itself authenticate users.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

class ReviewConflict(Exception):
    pass

class ReviewAccessDenied(Exception):
    pass

def _digest(prev, payload):
    return hashlib.sha256((prev + "\n" + payload).encode("utf-8")).hexdigest()

class SQLiteReviewAudit:
    def __init__(self, path):
        self.path = str(Path(path))
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS review_events (
                case_id TEXT NOT NULL, revision INTEGER NOT NULL,
                reviewer_id TEXT NOT NULL, payload TEXT NOT NULL,
                previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL,
                PRIMARY KEY(case_id, revision))""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS review_no_update
                BEFORE UPDATE ON review_events BEGIN SELECT RAISE(ABORT, 'append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS review_no_delete
                BEFORE DELETE ON review_events BEGIN SELECT RAISE(ABORT, 'append-only'); END""")

    def read(self, case_id):
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT revision, reviewer_id, payload, previous_hash, entry_hash "
                "FROM review_events WHERE case_id=? ORDER BY revision", (case_id,)
            ).fetchall()
        events = []
        previous = ""
        for revision, reviewer, payload, prior_hash, digest in rows:
            if revision != len(events) + 1 or prior_hash != previous or _digest(previous, payload) != digest:
                raise ValueError("audit integrity failure")
            events.append({"revision": revision, "reviewer_id": reviewer, **json.loads(payload),
                           "entry_hash": digest})
            previous = digest
        return events

    def append(self, *, case_id, expected_revision, trusted_reviewer_id,
               authorized, decision, evidence_refs, comment, reviewed_at):
        if not authorized or not trusted_reviewer_id:
            raise ReviewAccessDenied("trusted authorization required")
        if decision not in ("CONFIRMED", "REJECTED", "INSUFFICIENT"):
            raise ValueError("invalid documentary decision")
        if not case_id or not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 0:
            raise ValueError("invalid case/revision")
        if not comment or not reviewed_at or not isinstance(evidence_refs, list) or not evidence_refs:
            raise ValueError("missing supporting audit fields")
        data = {"decision": decision, "evidence_refs": evidence_refs,
                "comment": comment, "reviewed_at": reviewed_at,
                "economic_verdict": "REVIEW", "mutation_allowed": False}
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        with sqlite3.connect(self.path, timeout=10, isolation_level=None) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT revision, entry_hash FROM review_events "
                             "WHERE case_id=? ORDER BY revision DESC LIMIT 1", (case_id,)).fetchone()
            revision = row[0] if row else 0
            previous = row[1] if row else ""
            if revision != expected_revision:
                db.execute("ROLLBACK")
                raise ReviewConflict("stale review revision")
            digest = _digest(previous, payload)
            db.execute("INSERT INTO review_events VALUES (?,?,?,?,?,?)",
                       (case_id, revision + 1, trusted_reviewer_id, payload, previous, digest))
            db.execute("COMMIT")
        return {"case_id": case_id, "revision": revision + 1,
                "entry_hash": digest, "economic_verdict": "REVIEW",
                "mutation_allowed": False}

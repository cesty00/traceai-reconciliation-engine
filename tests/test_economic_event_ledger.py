import pytest

from traceai_reconciliation.investigation.economic_event_ledger import (
    EconomicEvent, EventOwnershipLedger, SourceLine,
)


def row(number, system="WMS"):
    return SourceLine(system, "sha256:test-export", number)


def event(name, sources, impact, status="CONFIRMED"):
    return EconomicEvent(name, tuple(sources), impact, status, "Documentary evidence")


def test_confirmed_impact_counts_each_physical_row_once():
    ledger = EventOwnershipLedger()
    ledger.register(event("a", [row(11), row(14, "WME")], -232.0))
    assert ledger.confirmed_impact == -232.0
    with pytest.raises(ValueError, match="already claimed"):
        ledger.register(event("duplicate", [row(11)], -232.0))
    assert ledger.confirmed_impact == -232.0
    assert len(ledger.events) == 1


def test_review_evidence_may_reference_confirmed_lines_but_adds_zero():
    ledger = EventOwnershipLedger()
    ledger.register(event("pv-review", [row(274988)], 0, "REVIEW"))
    ledger.register(event("validated", [row(274988)], -450))
    assert ledger.confirmed_impact == -450
    assert len(ledger.events) == 2


def test_identical_row_number_in_two_systems_not_collision():
    ledger = EventOwnershipLedger()
    ledger.register(event("wms", [row(10, "WMS")], -5))
    ledger.register(event("wme", [row(10, "WME")], 5))
    assert ledger.confirmed_impact == 0


def test_source_identity_requires_hash_and_physical_row():
    with pytest.raises(ValueError):
        SourceLine("WMS", "", 15)
    with pytest.raises(ValueError):
        SourceLine("WME", "sha", 0)


def test_review_cannot_claim_confirmed_nonzero_impact():
    with pytest.raises(ValueError, match="REVIEW"):
        event("unverified", [row(1)], 450, "REVIEW")


def test_duplicate_rows_and_event_ids_rejected():
    with pytest.raises(ValueError, match="Repeated"):
        event("duplicated", [row(1), row(1)], 0)
    ledger = EventOwnershipLedger()
    ledger.register(event("a", [row(1)], 0))
    with pytest.raises(ValueError, match="Duplicate economic event id"):
        ledger.register(event("a", [row(2)], 3))

"""GOV-002K: synthetic characterization, without CORE production changes.

These tests distinguish a working standalone ledger from as-yet-unproven
cross-matcher ownership in investigate_product.
"""
from __future__ import annotations

import inspect

import pytest

from traceai_reconciliation.investigation import engine
from traceai_reconciliation.investigation.economic_event_ledger import (
    EconomicEvent,
    EventOwnershipLedger,
    SourceLine,
)


def _line(system: str = "WMS") -> SourceLine:
    return SourceLine(system, "sha256:synthetic-export-v1", 17)


def _event(identifier: str, row: SourceLine, impact: float, status: str):
    return EconomicEvent(identifier, (row,), impact, status, "synthetic documentary evidence")


def test_gov_at_05_ledger_rejects_duplicate_confirmed_row_across_matcher_labels():
    """Unit-boundary evidence only: labels simulate two independent matchers."""
    ledger = EventOwnershipLedger()
    ledger.register(_event("delivery-matcher", _line(), -10.0, "CONFIRMED"))
    with pytest.raises(ValueError, match="already claimed"):
        ledger.register(_event("production-matcher", _line(), -10.0, "CONFIRMED"))
    assert ledger.confirmed_impact == -10.0
    assert [item.event_id for item in ledger.events] == ["delivery-matcher"]


def test_gov_at_06_review_remains_zero_before_one_confirmed_claim():
    ledger = EventOwnershipLedger()
    ledger.register(_event("delivery-candidate", _line("WME"), 0.0, "REVIEW"))
    ledger.register(_event("receipt-confirmed", _line("WME"), 10.0, "CONFIRMED"))
    assert ledger.confirmed_impact == 10.0
    assert len(ledger.events) == 2
    with pytest.raises(ValueError, match="REVIEW"):
        _event("unsafe-review", _line(), 10.0, "REVIEW")


@pytest.mark.xfail(
    strict=True,
    reason="GOV-AT-05/06 integration gate: CORE engine lacks demonstrated ledger wiring",
)
def test_gov_at_05_06_core_orchestration_uses_event_ownership_guard():
    """Intentional open gate, NOT acceptance of end-to-end economic ownership.

    The minimum integration prerequisite is an explicit EventOwnershipLedger
    reference in investigate_product; even after this turns XPASS, full
    source-backed cross-matcher scenario and delta arithmetic still need tests.
    """
    source = inspect.getsource(engine.investigate_product)
    assert "EventOwnershipLedger" in source

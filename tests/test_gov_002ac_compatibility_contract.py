"""GOV-002AC: compatibility characterization, no CORE runtime edits.

The existing provenance status is not operational equivalence or economic ownership.
"""
from dataclasses import fields
from test_gov_002w_provenance_probe import _sources
from traceai_reconciliation.investigation.provenance_adapter import (
    ReceiptProvenance, resolve_supplier_receipt_provenance,
)


def _resolve(data):
    wms, wme, production, index, *_ = data
    return resolve_supplier_receipt_provenance(
        index, wms_path=wms, wme_path=wme, production_path=production,
        product_code="SYN-W", product_name="Synthetic W", document="F88",
    )


def test_gov_002ac_legacy_receipt_provenance_contract_stays_intact(tmp_path):
    result = _resolve(_sources(tmp_path))
    assert result.status == "COMPLETE"
    assert result.reason == "SOURCE_ROWS_IDENTIFIED"
    assert len(result.source_lines) == 4
    assert [f.name for f in fields(ReceiptProvenance)] == [
        "status", "reason", "source_lines"
    ]
    # This confirms a candidate set, not individual operational equivalence.


def test_gov_002ac_provenance_does_not_expose_economic_confirmation(tmp_path):
    result = _resolve(_sources(tmp_path))
    assert "operational_equivalence" not in result.__dataclass_fields__
    assert "confirmed_economic_impact" not in result.__dataclass_fields__
    assert not hasattr(result, "matched_economic_event")
    # Contract must not treat COMPLETE as MATCH_DIRECT or CONFIRMED.


def test_gov_002ac_unavailable_source_never_has_candidates(tmp_path):
    data = _sources(tmp_path)
    wms, wme, production, index, *_ = data
    result = resolve_supplier_receipt_provenance(
        index, wms_path=wms, wme_path=wme, production_path=production,
        product_code="SYN-W", product_name="Synthetic W", document="MISSING"
    )
    assert result.status == "UNAVAILABLE"
    assert result.source_lines == ()

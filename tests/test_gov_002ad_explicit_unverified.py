"""GOV-002AD: additive, read-only operational status; backward-compatible shape."""
from dataclasses import fields
from test_gov_002w_provenance_probe import _sources
from traceai_reconciliation.investigation.provenance_adapter import (
    ReceiptProvenance, resolve_supplier_receipt_provenance,
)


def _read(data, document="F88"):
    wms,wme,production,index,*_=data
    return resolve_supplier_receipt_provenance(
        index,wms_path=wms,wme_path=wme,production_path=production,
        product_code="SYN-W",product_name="Synthetic W",document=document)


def test_gov_002ad_candidate_rows_are_not_operational_match(tmp_path):
    result=_read(_sources(tmp_path))
    assert result.status=="COMPLETE"
    assert result.operational_equivalence=="NOT_VERIFIED"
    assert len(result.source_lines)==4


def test_gov_002ad_unavailable_is_also_not_operational_match(tmp_path):
    result=_read(_sources(tmp_path),document="MISSING")
    assert result.status=="UNAVAILABLE" and result.source_lines==()
    assert result.operational_equivalence=="NOT_VERIFIED"


def test_gov_002ad_legacy_constructor_and_fields_remain_compatible():
    legacy=ReceiptProvenance("UNAVAILABLE","LEGACY_REASON")
    assert legacy.operational_equivalence=="NOT_VERIFIED"
    assert [x.name for x in fields(ReceiptProvenance)]==[
        "status","reason","source_lines"]

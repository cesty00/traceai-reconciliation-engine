from types import SimpleNamespace
import pytest
from traceai_reconciliation.investigation.bc_index_bridge import attach_bc_from_index
from traceai_reconciliation.reports import CaseReport

class Frame:
    def __init__(self, rows): self.rows=rows
    def to_dict(self, orient): return self.rows

class Index:
    def __init__(self, mismatch=False):
        self.mismatch=mismatch
    def source_manifest(self):
        return {"wms":{"file_name":"wms.csv","sha256":"a"*64},
                "wme":{"file_name":"wme.xlsx","sha256":("c" if self.mismatch else "b")*64}}
    def read_wms_product(self, code):
        return Frame([{"Cod articol":"10002","Numar comanda":"0023448_DC",
                       "Tip operatiune":"Ajustare negativa","Cod-motiv":"PRODUCTION-IN",
                       "Cantitate":-720,"SourceRowNumber":281807}])
    def read_wme_product(self, name):
        return Frame([{"OperationType":"BC","Document":"23448",
                       "WMEItemId":"1494","SignedQuantity":-90,
                       "SourceRowNumber":48162}]), {"1494"}

def report():
    r=CaseReport(case_id="CASE-10002",product_code="10002",product_name="CUTIE FRESH",
                 period="2026",report_date="2026-10-14",initial_difference=0,
                 explained_difference=0,unexplained_difference=0,unit="BUC",
                 verdict="REVIEW",evidence_level="D",cause_code="UNKNOWN",
                 cause_description="Not yet fully proven",cause_status="NEDETERMINATA",
                 executive_summary="BC difference")
    r.source_hashes.update({"wms_movements":"a"*64,"wme_ledger":"b"*64})
    r.conclusion_traceability.append({
        "step":"PRODUCTION_INPUT_BC","key":"BC=23448",
        "result":"WMS=-720.000; WME=-90.000; DIFF=-630.000",
    })
    return r

def test_bridge_adds_verified_documentary_link():
    r=report()
    assert attach_bc_from_index(r,Index(),"1494")==1
    assert any(x.get("step")=="BC_VERIFIED_SOURCE_LINK" for x in r.conclusion_traceability)
    assert r.verdict=="REVIEW"

def test_bridge_rejects_mismatched_source_hash_without_mutation():
    r=report()
    before=list(r.conclusion_traceability)
    with pytest.raises(ValueError,match="source identity"):
        attach_bc_from_index(r,Index(mismatch=True),"1494")
    assert r.conclusion_traceability==before

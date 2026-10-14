from zipfile import ZipFile
import pytest
from traceai_reconciliation.investigation.bc_row_link import link_bc_rows, append_verified_bc_link
from traceai_reconciliation.reports import CaseReport, generate_docx_report

def test_bc_source_link_in_docx(tmp_path):
    link = link_bc_rows(
        article_code="10002", bc_document="23448", wme_item_id="1494",
        wms_rows=[{"Cod articol":"10002","Numar comanda":"0023448_DC",
                   "Tip operatiune":"Ajustare negativa","Cod-motiv":"PRODUCTION-IN",
                   "SourceRowNumber":281807,"Cantitate":-720}],
        wme_rows=[{"WMEItemId":"1494","OperationType":"BC","Document":"23448",
                   "SourceRowNumber":48162,"SignedQuantity":-90}],
        source_manifest={"wms":{"file_name":"wms.csv","sha256":"a"*64},
                         "wme":{"file_name":"wme.xlsx","sha256":"b"*64}},
    )
    report = CaseReport(
        case_id="CASE-G1",product_code="10002",product_name="CUTIE FRESH",
        period="2026",report_date="2026-10-14",initial_difference=0,
        explained_difference=0,unexplained_difference=0,unit="BUC",
        verdict="REVIEW",evidence_level="D",cause_code="UNKNOWN",
        cause_description="Unverified stock cause",cause_status="NEDETERMINATA",
        executive_summary="Document quantity mismatch")
    report.conclusion_traceability.append({"step":"PRODUCTION_INPUT_BC","key":"BC=23448","result":"WMS=-720.000; WME=-90.000; DIFF=-630.000"})
    append_verified_bc_link(report, link)
    path=tmp_path/"case.docx"
    generate_docx_report(report,path)
    with ZipFile(path) as z:
        xml=z.read("word/document.xml").decode("utf-8")
    for token in ("BC=23448","WMS_ROW=281807","WME_ROW=48162",
                  "DIFF=-630.000","HUMAN_VALIDATION_NOT_ATTACHED"):
        assert token in xml
    assert report.verdict=="REVIEW"
    with pytest.raises(ValueError,match="already attached"):
        append_verified_bc_link(report,link)

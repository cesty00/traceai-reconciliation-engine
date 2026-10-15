from pathlib import Path
import pandas as pd
from docx import Document
from traceai_reconciliation.investigation.operation_timeline import timeline_from_wme
from traceai_reconciliation.reports.report_model import CaseReport
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx

def test_wme_column_p_users_reach_causes_docx(tmp_path: Path):
    wme = pd.DataFrame([
        dict(Note="UTIL_WME_A", Date="2026-02-08", Document="2250", OperationType="PV", SignedQuantity=-9832.28, Warehouse="SECTIE PRODUCTIE", SourceRowNumber=67192, LineNo=66902),
        dict(Note="UTIL_WME_B", Date="2026-06-09", Document="1067", OperationType="PV", SignedQuantity=33327.6, Warehouse="SECTIE PRODUCTIE", SourceRowNumber=67383, LineNo=67093),
    ])
    report = CaseReport(
        case_id="CASE-40024", product_code="40024", product_name="Etichete",
        period="2026", report_date="2026-10-15", initial_difference=-8620.2,
        explained_difference=0, unexplained_difference=-8620.2, unit="BUCATA",
        verdict="REVIEW", evidence_level="B", cause_code="REVIEW",
        cause_description="Pending", cause_status="NEDETERMINATA",
        executive_summary="Review",
        unmatched_operations=[
            dict(system="WME",document="2250",operation_type="PV",quantity=9832.28,reason="Review"),
            dict(system="WME",document="1067",operation_type="PV",quantity=-33327.6,reason="Review"),
        ],
        operation_timeline=timeline_from_wme(wme),
    )
    target=generate_operator_causes_docx(report,tmp_path/"case.docx")
    doc=Document(target)
    prose=" ".join(p.text for p in doc.paragraphs)
    assert "2250: UTIL_WME_A" in prose
    assert "1067: UTIL_WME_B" in prose
    assert report.verdict=="REVIEW"

from pathlib import Path
from docx import Document
from traceai_reconciliation.reports.report_model import CaseReport
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx

def test_case_40024_pv_candidate_is_not_auto_matched(tmp_path: Path):
    report = CaseReport(case_id="CASE-40024",product_code="40024",product_name="Etichete",
        period="2026",report_date="2026-10-15",initial_difference=-8620.2,
        explained_difference=0,unexplained_difference=-8620.2,unit="BUCATA",
        verdict="REVIEW",evidence_level="B",cause_code="REVIEW",
        cause_description="Investigatie",cause_status="NEDETERMINATA",
        executive_summary="Review",
        unmatched_operations=[
            dict(system="WME",document="2250",operation_type="PV",quantity=9832.28,reason="Review"),
            dict(system="WME",document="1067",operation_type="PV",quantity=-33327.6,reason="Review")],
        operation_timeline=[
            dict(system="WME",document="2250",operation_type="PV",quantity=-9832.28,date="2026-02-08",source_row=67192),
            dict(system="WMS",document="-",operation_type="Ajustare negativa",quantity=-9832.28,date="2026-02-08 17:29:04",source_row=275717),
            dict(system="WME",document="1067",operation_type="PV",quantity=33327.6,date="2026-06-09",source_row=67383),
            dict(system="WMS",document="-",operation_type="Ajustare pozitiva",quantity=33327.6,date="2026-06-07 14:49:45",source_row=275719),
        ])
    target=generate_operator_causes_docx(report,tmp_path/"case.docx")
    d=Document(target)
    txt=" ".join(p.text for p in d.paragraphs)+" "+" ".join(cell.text for tb in d.tables for row in tb.rows for cell in row.cells)
    assert "CORESPONDENȚE PV CANDIDATE" in txt
    for key in ["2250","1067","67192","67383","275717","275719"]:
        assert key in txt
    assert "NU SUNT MATCH CONFIRMATE" in txt
    assert report.verdict=="REVIEW"

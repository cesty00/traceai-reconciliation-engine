from pathlib import Path
from docx import Document
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx
from traceai_reconciliation.reports.report_model import CaseReport

def test_wms_details_blank_uses_required_label(tmp_path: Path):
    report=CaseReport(case_id="CASE-40024",product_code="40024",product_name="Etichete",
        period="2026",report_date="2026-10-16",initial_difference=-8620.2,
        explained_difference=0,unexplained_difference=-8620.2,unit="BUCATA",
        verdict="REVIEW",evidence_level="B",cause_code="REVIEW",
        cause_description="Pending",cause_status="NEDETERMINATA",
        executive_summary="Review",operation_timeline=[
            dict(system="WMS",document="-",operation_type="Ajustare negativa",date="2026-08-12",quantity=-8620,source_row=275716),
            dict(system="WMS",document="-",operation_type="Ajustare negativa",date="2026-08-12",quantity=-0.2,source_row=275715,wms_details="Inventar: verificare lot"),
        ])
    path=generate_operator_causes_docx(report,tmp_path/"case.docx")
    d=Document(path)
    cells=" ".join(cell.text for table in d.tables for row in table.rows for cell in row.cells)
    assert "motiv necompletat" in cells
    assert "Inventar: verificare lot" in cells
    assert report.verdict=="REVIEW"

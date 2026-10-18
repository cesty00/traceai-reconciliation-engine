from pathlib import Path
import pandas as pd
from docx import Document
from traceai_reconciliation.investigation.operation_timeline import timeline_from_wms
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx
from traceai_reconciliation.reports.report_model import CaseReport

def test_wms_details_reach_operator_report_verbatim(tmp_path: Path):
    frame=pd.DataFrame([{
        "Data":"2026-08-12 17:19:22","Tip operatiune":"Ajustare negativa",
        "Document":"-","Cantitate":-8620.0,"Gestiune":"Depozit Principal",
        "SourceRowNumber":275716,"Detalii":"Inventar intern / verificare lot 260709",
    }])
    events=timeline_from_wms(frame)
    assert events[0]["wms_details"]=="Inventar intern / verificare lot 260709"
    report=CaseReport(case_id="CASE-40024",product_code="40024",product_name="Etichete",
        period="2026",report_date="2026-10-16",initial_difference=-8620.2,
        explained_difference=0,unexplained_difference=-8620.2,unit="BUCATA",
        verdict="REVIEW",evidence_level="B",cause_code="REVIEW",
        cause_description="Pending",cause_status="NEDETERMINATA",
        executive_summary="Review",operation_timeline=events)
    path=generate_operator_causes_docx(report,tmp_path/"case.docx")
    doc=Document(path)
    content=" ".join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
    assert "Inventar intern / verificare lot 260709" in content
    assert "275716" in content
    assert report.verdict=="REVIEW"

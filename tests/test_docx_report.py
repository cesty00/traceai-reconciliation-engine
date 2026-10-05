from zipfile import ZipFile

from traceai_reconciliation.reports import (
    CaseReport,
    Recommendation,
    generate_docx_report,
    validate_case_report,
)


def make_report():
    return CaseReport(
        case_id="CASE-TEST-1",
        product_code="P1",
        product_name="Produs test",
        period="01.01.2026-02.01.2026",
        report_date="05.10.2026",
        initial_difference=10.0,
        explained_difference=7.0,
        unexplained_difference=3.0,
        unit="kg",
        verdict="REVIEW",
        evidence_level="C",
        cause_code="CAUSE-020",
        cause_description="Cauza necesita investigatie.",
        cause_status="NEDETERMINATA",
        executive_summary="Raport de test.",
        recommendations=[
            Recommendation("P1", "IMEDIATA", "Verifica documentele.")
        ],
    )


def test_validate_report_arithmetic():
    report = make_report()
    assert validate_case_report(report) == []

    report.unexplained_difference = 2.0
    errors = validate_case_report(report)
    assert any("Inconsistenta diferente" in item for item in errors)


def test_generate_docx(tmp_path):
    output = tmp_path / "report.docx"
    generate_docx_report(make_report(), output)

    assert output.exists()
    assert output.stat().st_size > 0

    with ZipFile(output) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")

    assert "CASE-TEST-1" in xml
    assert "Produs test" in xml
    assert "Recomandări de rezolvare" in xml

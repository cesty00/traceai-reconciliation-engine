from types import SimpleNamespace
from zipfile import ZipFile
from docx import Document
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx


def _case():
    return SimpleNamespace(
        case_id="CASE-TEST", report_date="2026-10-18", product_code="TEST",
        product_name="Synthetic", period="01.01.2026 - 11.10.2026",
        verdict="REVIEW", case_status="ASTEPTARE_VALIDARE", unit="Kilogram",
        findings=[], operation_timeline=[
            {"system": "WMS", "operation_type": "Receptie", "document": "IN100",
             "quantity": 5, "source_row": 17},
            {"system": "WME", "operation_type": "FE", "document": "FE200",
             "quantity": 5, "source_row": 23},
            {"system": "WMS", "operation_type": "Livrare", "document": "SFA300",
             "quantity": -2, "source_row": 31},
            {"system": "WME", "operation_type": "AE", "document": "300",
             "quantity": -2, "source_row": 41},
        ], unmatched_operations=[],
    )


def test_mapping_summary_never_calls_it_physical_discrepancy(tmp_path):
    details = {"stock_report_zone_matching": {
        "rows": [{"report_warehouse": "MOSTRE", "quantity_wms": 5,
                  "quantity_erp": 0, "wme_balance": 5,
                  "report_difference": 5, "actual_system_difference": 0,
                  "mapped_wme_warehouse": "MOSTRE",
                  "status": "REPORT_ERP_ZERO_MAPPING_CONFIRMED"}],
        "unresolved_rows": 0, "confirmed_report_mapping_rows": 1,
        "mapping_effect_total": 5,
    }, "receipt_matching": {"supported_documents": 1, "residual_total": 0},
       "delivery_matching": {"residual_total": 0}}
    target = tmp_path / "report.docx"
    generate_operator_causes_docx(_case(), target, details=details)
    with ZipFile(target) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Diferență de stoc REALĂ" not in xml
    assert "Diferență în RAPORTARE" in xml
    assert "IN100" in xml and "FE200" in xml
    assert "SFA300" in xml and "300" in xml
    assert "fără MATCH automat" in xml

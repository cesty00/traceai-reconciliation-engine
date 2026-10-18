from traceai_reconciliation.investigation.stock_report_zone_matching import StockReportZoneMatchResult, is_confirmed_reception_staging_offset

def test_operator_confirmed_staging_offset():
    result=StockReportZoneMatchResult(rows=[
      {"report_warehouse":"Depozitare","report_difference":-900},
      {"report_warehouse":"Recepție","report_difference":900},
    ],mapping_effect_total=0,confirmed_report_mapping_rows=[],unresolved_rows=[])
    assert is_confirmed_reception_staging_offset(result)

def test_other_gestiuni_do_not_get_automatic_staging_exception():
    result=StockReportZoneMatchResult(rows=[
      {"report_warehouse":"Depozitare","report_difference":-900},
      {"report_warehouse":"MOSE","report_difference":900},
    ],mapping_effect_total=0,confirmed_report_mapping_rows=[],unresolved_rows=[])
    assert not is_confirmed_reception_staging_offset(result)

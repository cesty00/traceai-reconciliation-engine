from traceai_reconciliation.mose_control.candidate_screen import candidate_screen


def wme(q=-5, date="2026-10-08", name="PRODUCT A", doc="900"):
    return dict(operation_type="F", product_name=name, date=date, quantity=q,
                document=doc, source_row=11)


def wms(q=-5, date="10/08/2026", name="PRODUCT A", order="SFA101", row=42):
    return dict(operation_type="Livrare", product_name=name, date=date,
                quantity=q, order=order, source_row=row)


def test_same_day_same_quantity_is_candidate_only():
    result = candidate_screen([wme()], [wms()])[0]
    assert result["candidate_count"] == 1
    assert result["verdict"] == "REVIEW"


def test_transfer_mose_excluded_from_customer_delivery_screen():
    assert candidate_screen([wme()], [wms(order="TRANSFER_MOSE-X")])[0]["candidate_count"] == 0


def test_positive_wme_reversal_not_assumed_customer_delivery():
    assert candidate_screen([wme(q=5)], [wms()])[0]["candidate_count"] == 0


def test_reused_wms_row_is_not_silently_consumed():
    items = candidate_screen([wme(doc="A"), wme(doc="B")], [wms()])
    assert [x["candidate_wms_source_rows"] for x in items] == [[42], [42]]
    assert all(x["verdict"] == "REVIEW" for x in items)


def test_bounded_candidates_report_truncation():
    result = candidate_screen([wme()], [wms(row=1), wms(row=2)], max_candidates_per_invoice=1)[0]
    assert result["candidate_count"] == 2
    assert result["candidates_truncated"] is True
    assert result["candidate_wms_source_rows"] == [1]


def test_numeric_wme_article_code_does_not_override_product_name():
    assert candidate_screen([dict(wme(), product_code="3711")], [wms(name="DIFFERENT")])[0]["candidate_count"] == 0

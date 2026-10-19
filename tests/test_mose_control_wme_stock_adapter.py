from traceai_reconciliation.mose_control.wme_stock_adapter import adapt_wme_stock_rows

def row(**changes):
    data = dict(Date="2026-10-10", Document="F100", OperationType="F",
                SignedQuantity=-10, Warehouse="MOSE", SourceRowNumber=40,
                Lot="L1", Balance=50, product_code="DS1")
    data.update(changes)
    return data

def test_source_row_provenance_preserved():
    assert adapt_wme_stock_rows([row()])["movements"][0]["source_row"] == 40

def test_missing_lot_blocks_replay():
    result = adapt_wme_stock_rows([row(Lot=None)])
    assert result["reasons"][0]["reason"] == "LOT_NOT_AVAILABLE"

def test_unmapped_wme_item_id_not_wms_code():
    result = adapt_wme_stock_rows([row(product_code=None, WMEItemId=20)])
    assert result["reasons"][0]["reason"] == "MISSING_SOURCE_IDENTITY"

def test_reported_balance_not_automatically_per_lot():
    result = adapt_wme_stock_rows([row(Balance=25)])
    assert result["movements"][0]["wme_reported_balance_unverified_scope"] == 25
    assert "observed_balance" not in result["movements"][0]

def test_missing_original_row_blocks():
    assert adapt_wme_stock_rows([row(SourceRowNumber=None)])["status"] == "BLOCKED_WITH_REASON"

def test_one_ambiguous_row_blocks_complete_replay():
    result = adapt_wme_stock_rows([row(), row(Lot="", SourceRowNumber=41)])
    assert result["status"] == "BLOCKED_WITH_REASON"
    assert result["movements"] == []

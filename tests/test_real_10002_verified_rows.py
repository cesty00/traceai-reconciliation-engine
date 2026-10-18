import pandas as pd
import pytest
from traceai_reconciliation.investigation.production_input_matching import match_production_inputs

def test_10002_real_bc_exports():
    # Original WMS/WME export rows, dated 2026-01-02. Item 10002 = ERP 1494.
    records = [
        ("2026-01-02 07:38:13", "0023448_DC", -720.0, 23448, -90.0, -630.0),
        ("2026-01-02 08:04:23", "0023454_DC", -400.0, 23454, -50.0, -350.0),
        ("2026-01-02 09:02:50", "0023462_DC", -880.0, 23462, -110.0, -770.0),
        ("2026-01-02 11:25:50", "0023467_DC", -400.0, 23467, -50.0, -350.0),
    ]
    wms = pd.DataFrame([
        {"Data": date, "Tip operatiune": "Ajustare negativa",
         "Cod-motiv": "PRODUCTION-IN", "Numar comanda": order,
         "Cantitate": qty, "Detalii": "Order production number: DECONGELARE " + order}
        for date, order, qty, _, _, _ in records
    ])
    wme = pd.DataFrame([
        {"OperationType": "BC", "Document": doc, "SignedQuantity": qty}
        for _, _, _, doc, qty, _ in records
    ])
    result = match_production_inputs(wms, wme)
    by_doc = {row["document"]: row for row in result.documents}
    for _, _, _, doc, _, difference in records:
        assert by_doc[str(doc)]["difference"] == pytest.approx(difference)
        assert by_doc[str(doc)]["status"] == "QTY_DIFF"
    assert result.residual_total == pytest.approx(-2100.0)
    assert result.persistent_residual_total == pytest.approx(-2100.0)

    assert len(result.persistent_residual_documents or []) == 4
    assert len(result.neutralized_residual_documents or []) == 0
    assert all(row["persistence_status"] == "PERSISTENT"
               for row in result.persistent_residual_documents)
    assert all(row["status"] == "QTY_DIFF" for row in result.documents)


@pytest.mark.parametrize(
    "order,wms_qty,document,wme_qty,difference,wms_row,wme_row",
    [
        ("0023448_DC", -720, 23448, -90, -630, 281807, 48162),
        ("0023454_DC", -400, 23454, -50, -350, 281823, 48161),
        ("0023462_DC", -880, 23462, -110, -770, 281841, 48159),
        ("0023467_DC", -400, 23467, -50, -350, 281842, 48160),
    ],
)
def test_individual_operator_confirmed_bc_is_not_match(
    order, wms_qty, document, wme_qty, difference, wms_row, wme_row,
):
    """Source-row references and human confirmations; no inferred automatic 8:1."""
    assert wms_row > 0 and wme_row > 0
    wms = pd.DataFrame([{
        "Data": "02.01.2026",
        "Tip operatiune": "Ajustare negativa",
        "Cod-motiv": "PRODUCTION-IN",
        "Numar comanda": order,
        "Cantitate": wms_qty,
        "Detalii": "Order production number: DECONGELARE " + order,
    }])
    wme = pd.DataFrame([{
        "OperationType": "BC", "Document": document,
        "SignedQuantity": wme_qty,
    }])
    result = match_production_inputs(wms, wme)
    assert len(result.documents) == 1
    assert str(result.documents[0]["document"]) == str(document)
    assert result.documents[0]["status"] == "QTY_DIFF"
    assert result.documents[0]["difference"] == pytest.approx(difference)
    assert result.persistent_residual_total == pytest.approx(difference)
    assert not (result.neutralized_residual_documents or [])

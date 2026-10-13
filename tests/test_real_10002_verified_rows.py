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

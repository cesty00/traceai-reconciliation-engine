from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.operation_timeline import (
    timeline_from_production,
    timeline_from_wme,
    timeline_from_wms,
)


def test_timeline_from_wms_maps_semantic_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "Data": "2026-10-13",
                "Document": "DOC-1",
                "TipOperatie": "Ajustare negativa",
                "Cantitate": -1.44,
                "Gestiune": "DP",
            }
        ]
    )

    rows = timeline_from_wms(frame)

    assert rows == [
        {
            "date": "2026-10-13",
            "system": "WMS",
            "source_row": None,  # Provenance must not be invented when the source lacks it.
            "document": "DOC-1",
            "operation_type": "Ajustare negativa",
            "quantity": -1.44,
            "warehouse": "DP",
            "counterpart": "-",
            "verdict": "REVIEW",
            "note": "Operațiune WMS extrasă automat pentru produs.",
        }
    ]


def test_timeline_from_wme_preserves_balance_context() -> None:
    frame = pd.DataFrame(
        [
            {
                "Date": "2026-10-13",
                "Document": "WME-1",
                "OperationType": "Livrare",
                "SignedQuantity": -2.0,
                "Warehouse": "DP",
                "Partner": "CLIENT",
                "Balance": 98.0,
            }
        ]
    )

    rows = timeline_from_wme(frame)

    assert rows[0]["system"] == "WME"
    assert rows[0]["document"] == "WME-1"
    assert rows[0]["quantity"] == -2.0
    assert rows[0]["counterpart"] == "CLIENT"
    assert rows[0]["note"] == "Sold după operațiune: 98.0"


def test_timeline_from_production_filters_to_requested_product() -> None:
    frame = pd.DataFrame(
        [
            {
                "TipLinie": "PREDARE",
                "PRE_Cod Articol": "DS001",
                "PRE_Cantitate Predare": 8.0,
                "PRE_U.M.": "KG",
                "Data Start": "2026-10-13",
                "Numar Comanda": "CMD-1",
                "Utilaj Productie": "ULMA",
            },
            {
                "TipLinie": "CONSUM",
                "CON_Cod Articol": "OTHER",
                "CON_Cantitate Consumata": 3.0,
                "CON_U.M.": "KG",
                "Data Start": "2026-10-13",
                "Numar Comanda": "CMD-2",
                "Utilaj Productie": "ULMA",
            },
        ]
    )

    rows = timeline_from_production(frame, "DS001")

    assert len(rows) == 1
    assert rows[0]["system"] == "PRODUCTIE"
    assert rows[0]["operation_type"] == "PREDARE"
    assert rows[0]["quantity"] == 8.0
    assert rows[0]["document"] == "CMD-1"


def test_timeline_builders_return_empty_for_empty_frames() -> None:
    empty = pd.DataFrame()

    assert timeline_from_wms(empty) == []
    assert timeline_from_wme(empty) == []
    assert timeline_from_production(empty, "DS001") == []

from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.stock_correction_matching import (
    match_generic_wms_stock_corrections,
)


def test_generic_correction_excludes_production_and_special_locations() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "11/01/2026 15:50:11",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -8.0,
                "Numar comanda": None,
                "Locatie sursa": "INS.DPP",
                "Cod-motiv": "COR STOC",
                "Lot": "356.25",
            },
            {
                "Data": "06/03/2026 14:00:17",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 680.0,
                "Numar comanda": "0027953_DC",
                "Locatie sursa": "ULMA",
                "Cod-motiv": "PRODUCTION-OUT",
                "Lot": "068.26",
            },
            {
                "Data": "06/03/2026 14:19:37",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -600.0,
                "Numar comanda": None,
                "Locatie sursa": "ULMA",
                "Cod-motiv": "COR STOC",
                "Lot": "068.26",
            },
            {
                "Data": "04/03/2026 20:50:35",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -618.0,
                "Numar comanda": None,
                "Locatie sursa": "INS.DET",
                "Cod-motiv": "COR STOC",
                "Lot": "019.26",
            },
        ]
    )

    result = match_generic_wms_stock_corrections(
        wms,
        excluded_locations={"INS.DET"},
    )

    assert result.residual_total == -8.0
    assert result.residual_corrections == [
        {
            "date": "11/01/2026 15:50:11",
            "quantity": -8.0,
            "location": "INS.DPP",
            "lot": "356.25",
            "document": "",
            "reason": (
                "COR STOC WMS fără document, în afara locațiilor de "
                "producție și a fluxurilor speciale deja tratate"
            ),
            "status": "WMS_ONLY_REVIEW",
        }
    ]

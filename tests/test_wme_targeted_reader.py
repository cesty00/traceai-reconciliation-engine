from __future__ import annotations

from pathlib import Path

import pandas as pd

from traceai_reconciliation.investigation.source_readers import read_wme_product


def test_targeted_wme_reader_returns_only_requested_product(tmp_path: Path) -> None:
    path = tmp_path / "wme.xlsx"
    rows = [
        [1, "NP", 101, "02.01.2026", 10.0, 0.0, 10.0, 0.0,
         "345", "TEST", "Produs A", "", 1001, "SECTIE PRODUCTIE", "KG", "", 1],
        [2, "AE", 102, "03.01.2026", 0.0, 2.0, 8.0, 0.0,
         "345", "TEST", "Produs B", "", 2002, "DEPOZIT", "KG", "", 2],
        [3, "PV", 103, "04.01.2026", 1.0, 0.0, 11.0, 0.0,
         "345", "TEST", "Produs A", "", 1001, "SECTIE PRODUCTIE", "KG", "", 3],
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)

    result, ids = read_wme_product(
        path,
        "Produs A",
        period="01.01.2026-31.01.2026",
    )

    assert len(result) == 2
    assert ids == {"1001"}
    assert set(result["OperationType"]) == {"NP", "PV"}
    assert float(result["SignedQuantity"].sum()) == 11.0
    assert result["Date"].notna().all()


def test_targeted_wme_reader_preserves_empty_result_contract(tmp_path: Path) -> None:
    path = tmp_path / "wme.xlsx"
    pd.DataFrame(
        [[1, "NP", 101, "02.01.2026", 1.0, 0.0, 1.0, 0.0,
          "345", "TEST", "Alt produs", "", 1001, "DP", "KG", "", 1]]
    ).to_excel(path, index=False, header=False)

    result, ids = read_wme_product(path, "Produs inexistent")

    assert result.empty
    assert list(result.columns)[-1] == "SignedQuantity"
    assert ids == set()

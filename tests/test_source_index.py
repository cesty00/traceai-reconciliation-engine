from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from traceai_reconciliation.investigation.source_index import (
    SQLiteSourceIndex,
)


def _write_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    wms = tmp_path / "wms.csv"
    production = tmp_path / "production.csv"
    wme = tmp_path / "wme.xlsx"

    pd.DataFrame(
        [
            {
                "Data": "1/2/2026 08:00:00",
                "Cod articol": "DS001",
                "Denumire articol": "Produs test",
                "Locatie sursa": "ULMA",
                "Locatie destinatie": "ULMA",
                "Palet sursa": "",
                "Palet destinatie": "",
                "Numar comanda": "001_AE",
                "Depozit": "DP",
                "Partener": "",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 10.0,
                "Persoana": "TEST",
                "Cod-motiv": "PRODUCTION-OUT",
                "Document intrare": "001_AE",
                "Document comanda": "001_AE",
                "Lot": "L1",
                "UM": "BUCATA",
                "Proprietar": "TEST",
                "Detalii": "",
            },
            {
                "Data": "1/2/2026 09:00:00",
                "Cod articol": "OTHER",
                "Denumire articol": "Alt produs",
                "Locatie sursa": "ULMA",
                "Locatie destinatie": "ULMA",
                "Palet sursa": "",
                "Palet destinatie": "",
                "Numar comanda": "002_AE",
                "Depozit": "DP",
                "Partener": "",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 5.0,
                "Persoana": "TEST",
                "Cod-motiv": "PRODUCTION-OUT",
                "Document intrare": "002_AE",
                "Document comanda": "002_AE",
                "Lot": "L2",
                "UM": "BUCATA",
                "Proprietar": "TEST",
                "Detalii": "",
            },
        ]
    ).to_csv(wms, sep=";", index=False)

    pd.DataFrame(
        [
            {
                "TipLinie": "PREDARE",
                "Numar Comanda": "001_AE",
                "Data Start": "1/2/2026 08:00:00",
                "PRE_Cod Articol": "DS001",
                "PRE_Cantitate Predare": 10.0,
                "PRE_U.M.": "BUCATA",
                "CON_Cod Articol": None,
                "CON_Cantitate Consumata": None,
                "CON_U.M.": None,
                "Utilaj Productie": "ULMA",
            },
            {
                "TipLinie": "CONSUM",
                "Numar Comanda": "003_AE",
                "Data Start": "1/3/2026 08:00:00",
                "PRE_Cod Articol": None,
                "PRE_Cantitate Predare": None,
                "PRE_U.M.": None,
                "CON_Cod Articol": "DS001",
                "CON_Cantitate Consumata": 2.0,
                "CON_U.M.": "BUCATA",
                "Utilaj Productie": "ULMA",
            },
        ]
    ).to_csv(production, sep=",", index=False)

    wme_rows = [
        ["Oceanis Seafood Europa S.R.L."] + [None] * 16,
        ["Fisa de magazie"] + [None] * 16,
        [
            1, "NP", 1, "02.01.2026", 10.0, 0.0, 10.0, 0.0,
            "345", "TEST", "Produs test", "", 1001,
            "SECTIE PRODUCTIE", "BUC", "", 1,
        ],
        [
            2, "AE", 2, "03.01.2026", 0.0, 2.0, 8.0, 0.0,
            "345", "TEST", "Alt produs", "", 2002,
            "DEPOZIT", "BUC", "", 2,
        ],
    ]
    pd.DataFrame(wme_rows).to_excel(
        wme,
        index=False,
        header=False,
    )
    return wms, wme, production


def test_sqlite_source_index_builds_and_filters_products(
    tmp_path: Path,
) -> None:
    wms, wme, production = _write_sources(tmp_path)
    index = SQLiteSourceIndex(tmp_path / "cache")

    rebuilt = index.ensure_index(wms, wme, production)
    assert rebuilt is True
    assert index.is_current(wms, wme, production) is True

    wms_rows = index.read_wms_product(
        "DS001",
        period="01.01.2026-31.01.2026",
    )
    assert len(wms_rows) == 1
    assert wms_rows.iloc[0]["Cod articol"] == "DS001"

    wme_rows, ids = index.read_wme_product(
        "Produs test",
        period="01.01.2026-31.01.2026",
    )
    assert len(wme_rows) == 1
    assert ids == {"1001"}
    assert float(wme_rows.iloc[0]["SignedQuantity"]) == 10.0

    assert index.count_wme_operation_document("NP", "1") == 1
    assert index.count_wme_operation_document("BC", "1") == 0
    assert index.count_wme_operation_document("AE", "2") == 1

    production_rows = index.read_production_product(
        "DS001",
        period="01.01.2026-31.01.2026",
    )
    assert len(production_rows) == 2

    reused = index.ensure_index(wms, wme, production)
    assert reused is False


def test_sqlite_source_index_invalidates_when_source_changes(
    tmp_path: Path,
) -> None:
    wms, wme, production = _write_sources(tmp_path)
    index = SQLiteSourceIndex(tmp_path / "cache")
    assert index.ensure_index(wms, wme, production) is True
    assert index.ensure_index(wms, wme, production) is False

    with wms.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n1/4/2026 10:00:00;DS002;Nou;"
            "ULMA;ULMA;;;;DP;;Ajustare pozitiva;1;"
            "TEST;PRODUCTION-OUT;;;;BUCATA;TEST;"
        )
    stat = wms.stat()
    os.utime(
        wms,
        ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000),
    )

    assert index.is_current(wms, wme, production) is False
    assert index.ensure_index(wms, wme, production) is True



def test_sqlite_source_index_reads_transfer_mose_and_mose_nt(
    tmp_path: Path,
) -> None:
    wms, wme, production = _write_sources(tmp_path)

    wms_frame = pd.read_csv(wms, sep=";")
    transfer_row = wms_frame.iloc[0].copy()
    transfer_row["Data"] = "1/4/2026 10:00:00"
    transfer_row["Cod articol"] = "DST"
    transfer_row["Denumire articol"] = "Produs transfer"
    transfer_row["Numar comanda"] = "TRANSFER_MOSE-TEST001"
    transfer_row["Tip operatiune"] = "Livrare"
    transfer_row["Cantitate"] = -5.0
    transfer_row["Partener"] = "DP->MOSE"
    transfer_row["Document intrare"] = None
    transfer_row["Document comanda"] = "40001"
    pd.concat(
        [wms_frame, pd.DataFrame([transfer_row])],
        ignore_index=True,
    ).to_csv(wms, sep=";", index=False)

    wme_frame = pd.read_excel(wme, header=None)
    nt_row = [
        3,
        "NT",
        9001,
        "04.01.2026",
        0.0,
        5.0,
        3.0,
        0.0,
        "345",
        "MOSE",
        "Produs transfer",
        "",
        3003,
        "DEPOZIT PRINCIPAL",
        "BUC",
        "",
        3,
    ]
    pd.concat(
        [wme_frame, pd.DataFrame([nt_row])],
        ignore_index=True,
    ).to_excel(wme, index=False, header=False)

    index = SQLiteSourceIndex(tmp_path / "cache")
    assert index.ensure_index(wms, wme, production) is True

    transfer_rows = index.read_wms_transfer_mose(
        period="01.01.2026-31.01.2026",
    )
    assert len(transfer_rows) == 1
    assert (
        transfer_rows.iloc[0]["Numar comanda"]
        == "TRANSFER_MOSE-TEST001"
    )

    nt_rows = index.read_wme_mose_nt(
        period="01.01.2026-31.01.2026",
    )
    assert len(nt_rows) == 1
    assert nt_rows.iloc[0]["OperationType"] == "NT"
    assert nt_rows.iloc[0]["Partner"] == "MOSE"

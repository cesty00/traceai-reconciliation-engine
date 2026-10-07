from __future__ import annotations

from pathlib import Path

from traceai_reconciliation.investigation.registry_backlog import (
    load_registry_export,
    manifest_payload,
    select_registry_cases,
    write_manifest,
)


def test_registry_selection_defaults_to_open_analysis_and_sorts_by_impact() -> None:
    rows = [
        {
            "CASE_ID": "CASE-2",
            "Perioada_WMS": "01.01.2026–04.10.2026",
            "Cod_produs": "DS002",
            "Diferenta": "-10,5",
            "Status_investigatie": "DESCHIS",
        },
        {
            "CASE_ID": "CASE-1",
            "Perioada_WMS": "01.01.2026–04.10.2026",
            "Cod_produs": "DS001",
            "Diferenta": "-100",
            "Status_investigatie": "IN_ANALIZA",
        },
        {
            "CASE_ID": "CASE-3",
            "Perioada_WMS": "01.01.2026–04.10.2026",
            "Cod_produs": "DS003",
            "Diferenta": "-999",
            "Status_investigatie": "ASTEPTARE_VALIDARE",
        },
    ]

    selected = select_registry_cases(rows)

    assert [case.case_id for case in selected] == [
        "CASE-1",
        "CASE-2",
    ]
    assert selected[0].period == "01.01.2026-04.10.2026"


def test_registry_selection_limit_and_exclusions() -> None:
    rows = [
        {
            "CASE_ID": "CASE-1",
            "Perioada_WMS": "P",
            "Cod_produs": "DS001",
            "Diferenta": "100",
            "Status_investigatie": "DESCHIS",
        },
        {
            "CASE_ID": "CASE-2",
            "Perioada_WMS": "P",
            "Cod_produs": "DS002",
            "Diferenta": "90",
            "Status_investigatie": "DESCHIS",
        },
        {
            "CASE_ID": "CASE-3",
            "Perioada_WMS": "P",
            "Cod_produs": "DS003",
            "Diferenta": "80",
            "Status_investigatie": "DESCHIS",
        },
    ]

    selected = select_registry_cases(
        rows,
        limit=1,
        exclude_case_ids={"CASE-1"},
        exclude_products={"DS003"},
    )

    assert [case.case_id for case in selected] == ["CASE-2"]


def test_registry_selection_deduplicates_case_id() -> None:
    rows = [
        {
            "CASE_ID": "CASE-1",
            "Perioada_WMS": "P",
            "Cod_produs": "DS001",
            "Diferenta": "10",
            "Status_investigatie": "DESCHIS",
        },
        {
            "CASE_ID": "CASE-1",
            "Perioada_WMS": "P",
            "Cod_produs": "DS001",
            "Diferenta": "20",
            "Status_investigatie": "DESCHIS",
        },
    ]

    selected = select_registry_cases(rows)
    assert len(selected) == 1


def test_registry_json_export_and_manifest_write(tmp_path: Path) -> None:
    source = tmp_path / "registry.json"
    source.write_text(
        """
        {
          "rows": [
            {
              "CASE_ID": "CASE-1",
              "Perioada_WMS": "01.01.2026–04.10.2026",
              "Cod_produs": "DS001",
              "Diferenta": "-12,5",
              "Status_investigatie": "DESCHIS"
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    rows = load_registry_export(source)
    cases = select_registry_cases(rows)
    output = write_manifest(tmp_path / "manifest.json", cases)

    assert output.exists()
    assert manifest_payload(cases) == {
        "cases": [
            {
                "case_id": "CASE-1",
                "product_code": "DS001",
                "period": "01.01.2026-04.10.2026",
                "report_date": None,
                "enabled": True,
            }
        ]
    }


def test_negative_limit_is_rejected() -> None:
    try:
        select_registry_cases([], limit=-1)
    except ValueError as exc:
        assert ">= 0" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

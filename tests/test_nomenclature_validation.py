from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.nomenclature_validation import (
    validate_nomenclature,
)


def test_empty_nomenclature_is_absent() -> None:
    assert validate_nomenclature(
        pd.DataFrame(),
        "DS001",
        "Produs",
    ) == ("ABSENT", "D")


def test_missing_code_column_is_absent() -> None:
    frame = pd.DataFrame([{"Denumire": "Produs"}])

    assert validate_nomenclature(
        frame,
        "DS001",
        "Produs",
    ) == ("ABSENT", "D")


def test_missing_product_code_is_flagged() -> None:
    frame = pd.DataFrame(
        [{"CodArticol": "DS999", "DenumireArticol": "Alt produs"}]
    )

    assert validate_nomenclature(
        frame,
        "DS001",
        "Produs",
    ) == ("COD_LIPSA", "C")


def test_code_without_name_column_is_confirmed_with_b_evidence() -> None:
    frame = pd.DataFrame([{"CodArticol": "DS001"}])

    assert validate_nomenclature(
        frame,
        "DS001",
        "Produs",
    ) == ("COD_CONFIRMAT", "B")


def test_exact_unique_name_is_a_evidence() -> None:
    frame = pd.DataFrame(
        [{"CodArticol": "DS001", "DenumireArticol": "Produs"}]
    )

    assert validate_nomenclature(
        frame,
        "DS001",
        "Produs",
    ) == ("COD_SI_DENUMIRE_CONFIRMATE", "A")


def test_same_name_with_multiple_names_is_ambiguous() -> None:
    frame = pd.DataFrame(
        [
            {"CodArticol": "DS001", "DenumireArticol": "Produs"},
            {"CodArticol": "DS001", "DenumireArticol": "Produs alternativ"},
        ]
    )

    assert validate_nomenclature(
        frame,
        "DS001",
        "Produs",
    ) == ("COD_CONFIRMAT_DENUMIRE_AMBIGUA", "B")


def test_different_name_is_c_evidence() -> None:
    frame = pd.DataFrame(
        [{"CodArticol": "DS001", "DenumireArticol": "Alt produs"}]
    )

    assert validate_nomenclature(
        frame,
        "DS001",
        "Produs",
    ) == ("COD_CONFIRMAT_DENUMIRE_DIFERITA", "C")

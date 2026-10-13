from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.product_identity import (
    resolve_product_identity,
)


def test_wms_unit_has_priority() -> None:
    result = resolve_product_identity(
        current_unit="UM",
        wms_rows=pd.DataFrame([{"UM": "KG"}]),
        wme_rows=pd.DataFrame([{"Unit": "BUC"}]),
        wme_ids={"1001"},
        product_code="DS001",
        product_name="Produs",
        nomenclature_status="COD_SI_DENUMIRE_CONFIRMATE",
    )

    assert result.unit == "KG"
    assert result.warnings == ()


def test_wme_unit_is_fallback_when_wms_unit_missing() -> None:
    result = resolve_product_identity(
        current_unit="UM",
        wms_rows=pd.DataFrame(),
        wme_rows=pd.DataFrame([{"Unit": "BUC"}]),
        wme_ids={"1001"},
        product_code="DS001",
        product_name="Produs",
        nomenclature_status="COD_SI_DENUMIRE_CONFIRMATE",
    )

    assert result.unit == "BUC"


def test_missing_wme_identity_adds_warning() -> None:
    result = resolve_product_identity(
        current_unit="KG",
        wms_rows=pd.DataFrame(),
        wme_rows=pd.DataFrame(),
        wme_ids=set(),
        product_code="DS001",
        product_name="Produs",
        nomenclature_status="COD_SI_DENUMIRE_CONFIRMATE",
    )

    assert result.warnings == (
        "Denumirea exactă 'Produs' nu a fost găsită în fișa WME.",
    )


def test_multiple_wme_ids_add_ambiguity_warning() -> None:
    result = resolve_product_identity(
        current_unit="KG",
        wms_rows=pd.DataFrame(),
        wme_rows=pd.DataFrame(),
        wme_ids={"1002", "1001"},
        product_code="DS001",
        product_name="Produs",
        nomenclature_status="COD_SI_DENUMIRE_CONFIRMATE",
    )

    assert result.warnings == (
        "Denumirea exactă 'Produs' este asociată cu mai multe ID-uri WME: "
        "['1001', '1002'].",
    )


def test_missing_nomenclature_code_keeps_mapping_review_warning() -> None:
    result = resolve_product_identity(
        current_unit="KG",
        wms_rows=pd.DataFrame(),
        wme_rows=pd.DataFrame(),
        wme_ids={"1001"},
        product_code="DS001",
        product_name="Produs",
        nomenclature_status="COD_LIPSA",
    )

    assert len(result.warnings) == 1
    assert "Codul DS001 lipsește din nomenclatorul încărcat." in result.warnings[0]
    assert "ID WME 1001" in result.warnings[0]

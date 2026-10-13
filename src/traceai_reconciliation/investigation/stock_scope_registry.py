"""Warehouse/zone scope registry. CANDIDATE is never an approved scope.

Entries transcribed from the existing Google Drive sheet:
Mapare_gestiuni_locatii_raport_stoc_WMS_WME_DE_VALIDAT
(Drive id 1YAkU9_OuP-_l7y25fGOs67gElVbPanw20S4nzb8S7UQ).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeMapping:
    report_zone: str
    wms_location: str | None
    wme_warehouse: str | None
    validation: str
    source: str


SOURCE = "DRIVE:1YAkU9_OuP-_l7y25fGOs67gElVbPanw20S4nzb8S7UQ"

CANDIDATE_MAPPINGS = (
    ScopeMapping("Depozitare", None, None, "CANDIDAT", SOURCE),
    ScopeMapping("Receptie", None, None, "CANDIDAT", SOURCE),
    ScopeMapping("SECTIE PRODUCTIE", None, "Sectie Productie", "CANDIDAT", SOURCE),
    ScopeMapping("DETERIORATE", None, "DETERIORATE", "CANDIDAT", SOURCE),
    ScopeMapping("MOSTRE", None, "MOSTRE", "CANDIDAT", SOURCE),
    ScopeMapping("PROTAN", None, "PROTAN", "CANDIDAT", SOURCE),
    ScopeMapping("PESTE PROASPAT", None, None, "NEVALIDAT", SOURCE),
)


def verify_aggregate_scope(*, zones: set[str], mappings: tuple[ScopeMapping, ...] = CANDIDATE_MAPPINGS) -> bool:
    """Fail closed unless EVERY relevant zone has a validated mapping.

    Presence of a candidate mapping is not documentary evidence of coverage.
    This routine is intentionally not a replacement for provenance-based
    validation of both legs of every internal transfer.
    """
    if not zones:
        return False
    index = {item.report_zone.casefold(): item for item in mappings}
    return all(
        (item := index.get(zone.strip().casefold())) is not None
        and item.validation == "VALIDAT"
        and bool(item.wms_location)
        and bool(item.wme_warehouse)
        for zone in zones
    )

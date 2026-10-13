from traceai_reconciliation.investigation.stock_scope_registry import (
    CANDIDATE_MAPPINGS, ScopeMapping, verify_aggregate_scope,
)


def test_real_drive_mapping_candidates_never_prove_aggregate_scope():
    assert {x.report_zone for x in CANDIDATE_MAPPINGS} >= {
        "Depozitare", "Receptie", "SECTIE PRODUCTIE", "DETERIORATE",
        "MOSTRE", "PROTAN", "PESTE PROASPAT",
    }
    assert not verify_aggregate_scope(zones={"Depozitare"})
    assert not verify_aggregate_scope(zones={"Depozitare", "Receptie"})


def test_only_approved_complete_mapping_is_eligible_for_scope_review():
    verified = (
        ScopeMapping("Zone A", "LOC_A", "3711", "VALIDAT", "manual-audit-1"),
        ScopeMapping("Zone B", "LOC_B", "301", "VALIDAT", "manual-audit-1"),
    )
    assert verify_aggregate_scope(zones={"Zone A", "Zone B"}, mappings=verified)
    assert not verify_aggregate_scope(zones={"Zone A", "Zone C"}, mappings=verified)
    assert not verify_aggregate_scope(zones=set(), mappings=verified)

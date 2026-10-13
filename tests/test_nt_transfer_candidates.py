from datetime import date
from traceai_reconciliation.investigation.nt_transfer_candidates import (
    TransferEvent, NTLeg, discover_transfer_candidates,
)


def _move(code, doc, qty):
    return TransferEvent(code,date(2026,3,21),doc,qty,"DEPAMBF","DEPAMB")


def test_real_50005_nt19462_remains_review():
    legs=(
        NTLeg("50005",date(2026,3,21),"19462","DEPOZIT PRINCIPAL",-64000),
        NTLeg("50005",date(2026,3,21),"19462","DEPOZIT PRINCIPAL",-32000),
        NTLeg("50005",date(2026,3,21),"19462","SECTIE PRODUCTIE",32000),
        NTLeg("50005",date(2026,3,21),"19462","SECTIE PRODUCTIE",64000),
    )
    result=discover_transfer_candidates([_move("50005","M8__03C19521",96000)],legs)
    assert result[0].nt_document=="19462"
    assert result[0].status=="REVIEW"


def test_same_day_competing_nt_cannot_be_matched():
    legs=(
        NTLeg("50005",date(2026,3,21),"19462","DEPOZIT PRINCIPAL",-96000),
        NTLeg("50005",date(2026,3,21),"19462","SECTIE PRODUCTIE",96000),
        NTLeg("50005",date(2026,3,21),"19463","DEPOZIT PRINCIPAL",-96000),
        NTLeg("50005",date(2026,3,21),"19463","SECTIE PRODUCTIE",96000),
    )
    result=discover_transfer_candidates([_move("50005","M8__03C19521",96000)],legs)
    assert result[0].nt_document is None
    assert result[0].reason=="MULTIPLE_NT_CANDIDATES"


def test_incomplete_nt_stays_review():
    legs=(NTLeg("50005",date(2026,3,21),"19462","DEPOZIT PRINCIPAL",-96000),)
    result=discover_transfer_candidates([_move("50005","M8__03C19521",96000)],legs)
    assert result[0].reason=="NO_VERIFIED_NT_CANDIDATE"

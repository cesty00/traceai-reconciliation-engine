"""CORE-UAT-01: synthetic regression inspired by authorized operator finding.

No original WMS/WME data is placed in the repository. The synthetic
magnitudes are illustrative and do not assert that CORE already emits
the proposed statuses.
"""
from dataclasses import dataclass
from typing import Literal

Reason = Literal["UNKNOWN", "PHYSICAL_INVENTORY"]


@dataclass(frozen=True)
class OperatorReview:
    article: str
    document: str
    difference: float
    wms_adjustment: float
    reason: Reason
    operator_confirmation: bool


def classify_review(case: OperatorReview):
    """Test-only contract: cause identification != justification/authorization."""
    evidence_coherent = abs(case.difference - case.wms_adjustment) < 1e-7
    return {
        "cause": "CAUSE_IDENTIFIED" if evidence_coherent else "REVIEW",
        "validation": ("OPERATOR_VALIDATED" if
                       evidence_coherent and case.operator_confirmation and
                       case.reason == "PHYSICAL_INVENTORY" else "OPERATIONAL_REVIEW"),
        "wme_adjustment_authorized": False,
        "automatic_match": False,
    }


def test_core_uat_01_unknown_reason_requires_operator_review():
    case=OperatorReview("SYN-REC-440","SYN-PV-60",-86.35,-86.35,"UNKNOWN",False)
    result=classify_review(case)
    assert result["cause"] == "CAUSE_IDENTIFIED"
    assert result["validation"] == "OPERATIONAL_REVIEW"
    assert not result["wme_adjustment_authorized"]
    assert not result["automatic_match"]


def test_core_uat_01_inventory_confirmed_only_validates_reason():
    case=OperatorReview("SYN-REC-440","SYN-PV-60",-86.35,-86.35,"PHYSICAL_INVENTORY",True)
    result=classify_review(case)
    assert result["cause"] == "CAUSE_IDENTIFIED"
    assert result["validation"] == "OPERATOR_VALIDATED"
    assert not result["wme_adjustment_authorized"]
    assert not result["automatic_match"]


def test_core_uat_01_confirmation_does_not_override_unexplained_difference():
    case=OperatorReview("SYN-REC-440","SYN-PV-60",-86.35,-80.0,"PHYSICAL_INVENTORY",True)
    result=classify_review(case)
    assert result["cause"] == "REVIEW"
    assert result["validation"] == "OPERATIONAL_REVIEW"

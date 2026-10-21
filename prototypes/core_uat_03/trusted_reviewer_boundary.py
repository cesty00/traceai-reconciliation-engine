"""Isolated boundary for trusted reviewer identity; no production auth provider.

A server-created context can be accepted ONLY after an external authenticated
provider has verified the principal and granted access to a specific case.
Form-controlled user IDs are never credentials.
"""
from dataclasses import dataclass
from typing import FrozenSet, Mapping

class IdentityDenied(PermissionError):
    pass

@dataclass(frozen=True)
class VerifiedPrincipal:
    subject_id: str
    provider: str
    roles: FrozenSet[str]
    allowed_cases: FrozenSet[str]
    authenticated: bool

def authorize_document_review(principal: VerifiedPrincipal | None, case_id: str,
                              form: Mapping[str, object]) -> dict:
    if not isinstance(principal, VerifiedPrincipal) or not principal.authenticated:
        raise IdentityDenied("authenticated principal required")
    if not principal.subject_id or not principal.provider:
        raise IdentityDenied("incomplete trusted principal")
    if "document_reviewer" not in principal.roles or case_id not in principal.allowed_cases:
        raise IdentityDenied("case review not permitted")
    for forbidden in ("reviewer_id", "authorized", "roles", "subject_id", "session_id"):
        if forbidden in form:
            raise IdentityDenied("identity or permissions supplied by form")
    if form.get("decision") not in ("CONFIRMED", "REJECTED", "INSUFFICIENT"):
        raise ValueError("invalid review decision")
    return {"case_id": case_id, "trusted_reviewer_id": principal.subject_id,
            "decision": form["decision"], "authorized": True,
            "economic_verdict": "REVIEW", "mutation_allowed": False}

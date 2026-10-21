import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).parents[1]/"prototypes/core_uat_03/trusted_reviewer_boundary.py"
spec=importlib.util.spec_from_file_location("auth",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def principal(**changes):
    d={"subject_id":"SYN-REVIEWER","provider":"SYN-IDP","roles":frozenset({"document_reviewer"}),
       "allowed_cases":frozenset({"SYN-CASE"}),"authenticated":True}
    d.update(changes)
    return m.VerifiedPrincipal(**d)
def test_trusted_principal_case_review():
    result=m.authorize_document_review(principal(),"SYN-CASE",{"decision":"CONFIRMED"})
    assert result["trusted_reviewer_id"]=="SYN-REVIEWER"
    assert result["economic_verdict"]=="REVIEW" and not result["mutation_allowed"]
def test_unauthenticated_denied():
    with pytest.raises(m.IdentityDenied):m.authorize_document_review(principal(authenticated=False),"SYN-CASE",{"decision":"CONFIRMED"})
def test_cross_case_denied():
    with pytest.raises(m.IdentityDenied):m.authorize_document_review(principal(),"OTHER",{"decision":"CONFIRMED"})
def test_role_denied():
    with pytest.raises(m.IdentityDenied):m.authorize_document_review(principal(roles=frozenset()),"SYN-CASE",{"decision":"CONFIRMED"})
def test_form_spoof_denied():
    with pytest.raises(m.IdentityDenied):m.authorize_document_review(principal(),"SYN-CASE",{"decision":"CONFIRMED","reviewer_id":"OTHER"})

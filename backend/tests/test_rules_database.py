import pytest
from services.rules_database import RulesDatabaseService, rules_db

def test_get_cpt_code():
    cpt = rules_db.get_cpt_code("73721")
    assert cpt is not None
    assert cpt["code"] == "73721"
    assert cpt["requires_prior_authorization"] is True
    assert cpt["allowed_amount"] == 850.0

def test_get_icd_code():
    icd = rules_db.get_icd_code("M25.561")
    assert icd is not None
    assert icd["code"] == "M25.561"
    assert icd["description"] == "Pain in right knee"

def test_get_preauth_rule():
    rule = rules_db.get_preauth_rule("73721")
    assert rule is not None
    assert rule["requires_preauth"] is True
    assert len(rule["clinical_criteria"]) > 0

def test_is_preauth_required():
    assert rules_db.is_preauth_required("73721") is True
    assert rules_db.is_preauth_required("97110") is False

def test_list_codes():
    cpts = rules_db.list_cpt_codes()
    icds = rules_db.list_icd_codes()
    assert len(cpts) > 0
    assert len(icds) > 0

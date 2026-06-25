import pytest
from pathlib import Path

from app.schemas.insurance_engine import CoverageDecision
from services.insurance_engine import InsuranceService


def test_insurance_service_initialization():
    """Verify that InsuranceService initializes and loads mock policies correctly."""
    service = InsuranceService()
    assert len(service._policies) >= 2
    assert "BS-120-BLUE" in service._policies
    assert "UH-990-GOLD" in service._policies


def test_get_policy():
    """Verify retrieving policies by subscriber and dependent member IDs."""
    service = InsuranceService()

    # BlueShield policy checks (Plan A)
    policy_a = service.get_policy("98765")  # Priya (Subscriber)
    assert policy_a is not None
    assert policy_a.policy_id == "BS-120-BLUE"
    assert policy_a.provider_name == "BlueShield Cross"

    policy_a_dep = service.get_policy("98765-02")  # Aarav (Dependent)
    assert policy_a_dep is not None
    assert policy_a_dep.policy_id == "BS-120-BLUE"

    # UnitedHealth policy checks (Plan B)
    policy_b = service.get_policy("12345")  # Dev (Subscriber)
    assert policy_b is not None
    assert policy_b.policy_id == "UH-990-GOLD"
    assert policy_b.provider_name == "UnitedHealth"

    policy_b_dep = service.get_policy("12345-02")  # Priya (Dependent)
    assert policy_b_dep is not None
    assert policy_b_dep.policy_id == "UH-990-GOLD"

    policy_b_dep2 = service.get_policy("12345-03")  # Aarav (Dependent)
    assert policy_b_dep2 is not None
    assert policy_b_dep2.policy_id == "UH-990-GOLD"

    # Non-existent member ID
    non_existent = service.get_policy("99999")
    assert non_existent is None


def test_get_member_role():
    """Verify correct role resolution for subscribers and dependents."""
    service = InsuranceService()

    assert service.get_member_role("98765") == "subscriber"
    assert service.get_member_role("98765-02") == "dependent"
    assert service.get_member_role("12345") == "subscriber"
    assert service.get_member_role("12345-02") == "dependent"
    assert service.get_member_role("12345-03") == "dependent"
    assert service.get_member_role("99999") is None


def test_is_procedure_covered():
    """Verify procedure coverage logic against rule definitions."""
    service = InsuranceService()

    # BlueShield (98765)
    assert service.is_procedure_covered("98765", "97161") is True
    assert service.is_procedure_covered("98765", "29881") is True
    assert service.is_procedure_covered("98765", "99999") is False

    # UnitedHealth (12345-03)
    assert service.is_procedure_covered("12345-03", "73721") is True
    assert service.is_procedure_covered("12345-03", "29881") is True
    assert service.is_procedure_covered("12345-03", "99999") is False

    # Non-existent member ID
    assert service.is_procedure_covered("99999", "97161") is False


def test_requires_preauthorization():
    """Verify pre-authorization rule checks."""
    service = InsuranceService()

    # BlueShield preauth rules
    assert service.requires_preauthorization("98765", "97161") is False
    assert service.requires_preauthorization("98765", "29881") is True

    # UnitedHealth preauth rules (Plan B has different rules)
    assert service.requires_preauthorization("12345-03", "73721") is True  # MRI needs preauth
    assert service.requires_preauthorization("12345-03", "29881") is False  # Surgery does not need preauth

    # Non-existent member ID / CPT code
    assert service.requires_preauthorization("99999", "97161") is False
    assert service.requires_preauthorization("98765", "99999") is False


def test_evaluate_coverage_decision():
    """Verify detailed CoverageDecision schema generation."""
    service = InsuranceService()

    # Case 1: Covered, requires preauth (BlueShield, CPT 29881)
    decision1 = service.evaluate_coverage("98765", "29881")
    assert isinstance(decision1, CoverageDecision)
    assert decision1.is_covered is True
    assert decision1.requires_preauth is True
    assert decision1.deductible_applies is True
    assert decision1.coinsurance_rate == 0.20
    assert "Pre-authorization IS required" in decision1.message
    assert "conservative therapy failure" in decision1.message

    # Case 2: Covered, no preauth (UnitedHealth, CPT 29881)
    decision2 = service.evaluate_coverage("12345-03", "29881")
    assert decision2.is_covered is True
    assert decision2.requires_preauth is False
    assert decision2.deductible_applies is True
    assert decision2.coinsurance_rate == 0.10
    assert "No pre-authorization required" in decision2.message

    # Case 3: Member not found
    decision3 = service.evaluate_coverage("99999", "97161")
    assert decision3.is_covered is False
    assert "not found" in decision3.message

    # Case 4: CPT code not recognized
    decision4 = service.evaluate_coverage("98765", "99999")
    assert decision4.is_covered is False
    assert "not recognized" in decision4.message

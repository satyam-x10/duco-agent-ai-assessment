"""
Comprehensive COB Test Suite verifying:
1. Contractual fee schedule allowed amounts vs billed amounts & contractual write-offs
2. Primary and secondary fixed copays with deductible/coinsurance interaction
3. Secondary coordination under the statutory NAIC 'lesser-of' rule
4. Multi-member family deductible rollover & exhaustion across sequential claims
5. Out-of-Pocket Maximum (OOPM) saturation & patient liability caps
6. Strict conservation law invariant across complex dual-coverage claims
"""

from decimal import Decimal
import pytest

from app.schemas.insurance_engine import (
    InsurancePolicy,
    Member,
    CoverageRule,
    Deductible,
    Coinsurance,
)
from app.schemas.cob_engine import Claim, ClaimLine
from services.insurance_engine import InsuranceService
from services.cob_engine import COBEngine
from services.finance_engine import FinanceEngine


@pytest.fixture
def dual_insurance_service():
    """Creates an InsuranceService populated with versioned primary and secondary policies."""
    pri_policy = InsurancePolicy(
        policy_id="PRI-POL-100",
        provider_name="Primary Health Plan",
        group_number="GRP100",
        policy_version="2026.1-PROD",
        source_regulation="NAIC Model COB #120",
        effective_date="2026-01-01",
        deductible=Deductible(individual=20000.0, family=40000.0, remaining_individual=10000.0, remaining_family=25000.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=50000.0,
        remaining_out_of_pocket_max=30000.0,
        members=[
            Member(member_id="MEM-01", first_name="Priya", last_name="Sen", role="subscriber", relationship_to_subscriber="self", date_of_birth="1985-04-12"),
            Member(member_id="MEM-02", first_name="Aarav", last_name="Sen", role="dependent", relationship_to_subscriber="child", date_of_birth="2012-05-14"),
        ],
        coverage_rules=[
            CoverageRule(cpt_code="97161", is_covered=True, requires_preauth=False, allowed_amount=15000.0, copay=2000.0, deductible_applies=True),
            CoverageRule(cpt_code="97110", is_covered=True, requires_preauth=False, allowed_amount=8000.0, copay=1000.0, deductible_applies=True),
            CoverageRule(cpt_code="73721", is_covered=True, requires_preauth=False, allowed_amount=12000.0, copay=0.0, deductible_applies=True),
            CoverageRule(cpt_code="29881", is_covered=True, requires_preauth=True, allowed_amount=90000.0, copay=5000.0, deductible_applies=True),
        ]
    )

    sec_policy = InsurancePolicy(
        policy_id="SEC-POL-200",
        provider_name="Secondary Health Plan",
        group_number="GRP200",
        policy_version="2026.1-PROD",
        source_regulation="NAIC Model COB #120",
        effective_date="2026-01-01",
        deductible=Deductible(individual=15000.0, family=30000.0, remaining_individual=5000.0, remaining_family=15000.0),
        coinsurance=Coinsurance(rate=0.10),
        out_of_pocket_max=40000.0,
        remaining_out_of_pocket_max=20000.0,
        members=[
            Member(member_id="SEC-01", first_name="Rajesh", last_name="Sen", role="subscriber", relationship_to_subscriber="self", date_of_birth="1983-09-20"),
            Member(member_id="SEC-02", first_name="Aarav", last_name="Sen", role="dependent", relationship_to_subscriber="child", date_of_birth="2012-05-14"),
            Member(member_id="SEC-03", first_name="Priya", last_name="Sen", role="dependent", relationship_to_subscriber="spouse", date_of_birth="1985-04-12"),
        ],
        coverage_rules=[
            CoverageRule(cpt_code="97161", is_covered=True, requires_preauth=False, allowed_amount=18000.0, copay=1000.0, deductible_applies=True),
            CoverageRule(cpt_code="97110", is_covered=True, requires_preauth=False, allowed_amount=9000.0, copay=500.0, deductible_applies=True),
            CoverageRule(cpt_code="73721", is_covered=True, requires_preauth=False, allowed_amount=12000.0, copay=0.0, deductible_applies=True),
            CoverageRule(cpt_code="29881", is_covered=True, requires_preauth=False, allowed_amount=95000.0, copay=0.0, deductible_applies=True),
        ]
    )

    service = InsuranceService()
    service._policies = {pri_policy.policy_id: pri_policy, sec_policy.policy_id: sec_policy}
    service._family_deductibles = {
        pri_policy.policy_id: pri_policy.deductible.remaining_family,
        sec_policy.policy_id: sec_policy.deductible.remaining_family,
    }
    service._member_accumulators = {
        f"{pri_policy.policy_id}:MEM-01": {
            "remaining_individual_deductible": pri_policy.deductible.remaining_individual,
            "remaining_out_of_pocket_max": pri_policy.remaining_out_of_pocket_max,
        },
        f"{pri_policy.policy_id}:MEM-02": {
            "remaining_individual_deductible": pri_policy.deductible.remaining_individual,
            "remaining_out_of_pocket_max": pri_policy.remaining_out_of_pocket_max,
        },
        f"{sec_policy.policy_id}:SEC-02": {
            "remaining_individual_deductible": sec_policy.deductible.remaining_individual,
            "remaining_out_of_pocket_max": sec_policy.remaining_out_of_pocket_max,
        },
        f"{sec_policy.policy_id}:SEC-03": {
            "remaining_individual_deductible": sec_policy.deductible.remaining_individual,
            "remaining_out_of_pocket_max": sec_policy.remaining_out_of_pocket_max,
        },
    }
    return service


def test_contractual_allowed_amount_and_writeoff(dual_insurance_service):
    """
    Test fee schedule discount:
    CPT 97161 Billed: ₹20,000. Primary Allowed: ₹15,000 (Write-off: ₹5,000).
    Primary Copay: ₹2,000. Remaining allowed subject to deductible: ₹13,000.
    Primary Remaining Ded: ₹10,000 (Ded Applied: ₹10,000).
    Subject to coinsurance: ₹3,000 * 20% = ₹600.
    Primary Paid = ₹3,000 - ₹600 = ₹2,400.
    Primary Patient Responsibility before Secondary = ₹2,000 (copay) + ₹10,000 (ded) + ₹600 (coins) = ₹12,600.
    """
    cob_engine = COBEngine(dual_insurance_service)
    claim = Claim(
        claim_id="TEST-ALLOWED-01",
        member_id="MEM-01",
        diagnoses=["M54.50"],
        lines=[
            ClaimLine(cpt_code="97161", billed_amount=20000.0, member_id="MEM-01", diagnoses=["M54.50"]),
        ]
    )

    decision = cob_engine.coordinate_benefits(claim)
    assert len(decision.lines_coverage) == 1
    line = decision.lines_coverage[0]

    # Primary checks
    assert line.primary_coverage.allowed_amount == 15000.0
    assert line.primary_coverage.contractual_writeoff == 5000.0
    assert line.primary_coverage.copay_applied == 2000.0
    assert line.primary_coverage.deductible_applied == 10000.0
    assert line.primary_coverage.coinsurance_amount == 600.0
    assert line.primary_coverage.primary_paid == 2400.0
    assert line.primary_coverage.patient_responsibility == 12600.0

    # Secondary coordination checks
    assert line.secondary_coverage.is_covered is True
    assert line.secondary_coverage.secondary_paid > 0.0

    # Financial Conservation check
    finance_engine = FinanceEngine()
    report = finance_engine.generate_financial_breakdown(decision)
    summary = report.breakdown.summary

    total_accounted = (
        Decimal(str(summary.total_primary_paid))
        + Decimal(str(summary.total_secondary_paid))
        + Decimal(str(line.primary_coverage.contractual_writeoff))
        + Decimal(str(summary.total_patient_responsibility))
    )
    assert total_accounted == Decimal(str(summary.total_billed))


def test_secondary_lesser_of_normal_benefit_coordination(dual_insurance_service):
    """
    Verify secondary insurer pays the lesser of the remaining patient responsibility
    and its own normal benefit calculation.
    """
    cob_engine = COBEngine(dual_insurance_service)
    claim = Claim(
        claim_id="TEST-LESSER-OF-01",
        member_id="MEM-02",
        diagnoses=["M23.231"],
        lines=[
            ClaimLine(cpt_code="29881", billed_amount=100000.0, member_id="MEM-02", diagnoses=["M23.231"]),
        ]
    )

    decision = cob_engine.coordinate_benefits(claim)
    line = decision.lines_coverage[0]

    # Primary pays based on allowed amount ₹90,000, copay ₹5,000, ded ₹10,000, coins 20%
    assert line.primary_coverage.is_covered is True
    assert line.secondary_coverage.is_covered is True
    # Secondary must coordinate and cover part of primary patient responsibility
    assert line.secondary_coverage.secondary_paid > 0.0
    assert line.remaining_balance.patient_responsibility < line.primary_coverage.patient_responsibility


def test_multi_member_family_deductible_exhaustion(dual_insurance_service):
    """
    Verify that sequential claims by different family members (Priya MEM-01 and Aarav MEM-02)
    properly accumulate against and exhaust the shared family deductible.
    """
    cob_engine = COBEngine(dual_insurance_service)

    # Claim 1: Priya has billed amount that reduces family deductible by ₹10,000
    claim_priya = Claim(
        claim_id="CLAIM-FAM-01",
        member_id="MEM-01",
        diagnoses=["M54.50"],
        lines=[
            ClaimLine(cpt_code="97161", billed_amount=15000.0, member_id="MEM-01", diagnoses=["M54.50"]),
        ]
    )
    dec_priya = cob_engine.coordinate_benefits(claim_priya)
    assert dec_priya.lines_coverage[0].primary_coverage.deductible_applied == 10000.0

    # Family deductible remaining before was ₹25,000 -> now ₹15,000
    assert dual_insurance_service._family_deductibles["PRI-POL-100"] == 15000.0

    # Claim 2: Aarav has claim that applies remaining individual deductible of ₹10,000
    claim_aarav = Claim(
        claim_id="CLAIM-FAM-02",
        member_id="MEM-02",
        diagnoses=["M23.231"],
        lines=[
            ClaimLine(cpt_code="73721", billed_amount=12000.0, member_id="MEM-02", diagnoses=["M23.231"]),
        ]
    )
    dec_aarav = cob_engine.coordinate_benefits(claim_aarav)
    assert dec_aarav.lines_coverage[0].primary_coverage.deductible_applied == 10000.0

    # Family deductible remaining now ₹5,000
    assert dual_insurance_service._family_deductibles["PRI-POL-100"] == 5000.0


def test_oop_maximum_cap_protection():
    """
    Verify that when patient liability reaches the remaining Out-of-Pocket Max,
    the insurer pays 100% of excess charges and patient liability is capped.
    """
    policy = InsurancePolicy(
        policy_id="OOP-CAP-POL",
        provider_name="Cap Health",
        group_number="GRP-CAP",
        policy_version="2026.1-PROD",
        source_regulation="ACA Sec. 2707 / 45 CFR 156.130",
        deductible=Deductible(individual=10000.0, family=20000.0, remaining_individual=0.0, remaining_family=0.0),
        coinsurance=Coinsurance(rate=0.50),  # High 50% coinsurance
        out_of_pocket_max=5000.0,
        remaining_out_of_pocket_max=2000.0,  # Only ₹2,000 left until OOPM
        members=[
            Member(member_id="CAP-MEM", first_name="Sam", last_name="Patel", role="subscriber", relationship_to_subscriber="self", date_of_birth="1990-01-01")
        ],
        coverage_rules=[
            CoverageRule(cpt_code="73721", is_covered=True, requires_preauth=False, allowed_amount=10000.0, copay=0.0, deductible_applies=False),
        ]
    )

    service = InsuranceService()
    service._policies = {policy.policy_id: policy}
    service._family_deductibles = {policy.policy_id: 0.0}
    service._member_accumulators = {
        f"{policy.policy_id}:CAP-MEM": {
            "remaining_individual_deductible": 0.0,
            "remaining_out_of_pocket_max": 2000.0,
        }
    }

    cob = COBEngine(service)
    claim = Claim(
        claim_id="CLAIM-OOP-01",
        member_id="CAP-MEM",
        diagnoses=["M23.231"],
        lines=[
            ClaimLine(cpt_code="73721", billed_amount=10000.0, member_id="CAP-MEM", diagnoses=["M23.231"]),
        ]
    )

    decision = cob.coordinate_benefits(claim)
    line = decision.lines_coverage[0]

    # Standard 50% coinsurance would be ₹5,000 patient responsibility, but OOP cap is ₹2,000!
    assert line.primary_coverage.patient_responsibility == 2000.0
    # Insurer pays remainder: ₹10,000 - ₹2,000 = ₹8,000
    assert line.primary_coverage.primary_paid == 8000.0
    assert line.remaining_balance.patient_responsibility == 2000.0

from decimal import Decimal
from services.insurance_engine import InsuranceService
from services.cob_engine import COBEngine
from app.schemas.insurance_engine import InsurancePolicy, Member, CoverageRule, Deductible, Coinsurance
from app.schemas.cob_engine import Claim, ClaimLine


def test_conservation_law_and_allowed_amounts_with_copay():
    """Verify that primary + secondary + patient responsibility + contractual writeoff == billed amount."""
    service = InsuranceService()
    service._policies.clear()

    policy_a = InsurancePolicy(
        policy_id="PLAN-A",
        provider_name="Primary Payer",
        group_number="GRP-A",
        deductible=Deductible(individual=10000.0, family=25000.0, remaining_individual=5000.0, remaining_family=10000.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=50000.0,
        remaining_out_of_pocket_max=30000.0,
        members=[Member(member_id="M-101", first_name="John", last_name="Doe", role="subscriber", relationship_to_subscriber="self", date_of_birth="1980-01-01")],
        coverage_rules=[
            CoverageRule(cpt_code="97161", is_covered=True, requires_preauth=False, allowed_amount=15000.0, copay=1000.0, deductible_applies=True)
        ]
    )

    policy_b = InsurancePolicy(
        policy_id="PLAN-B",
        provider_name="Secondary Payer",
        group_number="GRP-B",
        deductible=Deductible(individual=15000.0, family=30000.0, remaining_individual=8000.0, remaining_family=15000.0),
        coinsurance=Coinsurance(rate=0.10),
        out_of_pocket_max=60000.0,
        remaining_out_of_pocket_max=40000.0,
        members=[Member(member_id="M-101-DEP", first_name="John", last_name="Doe", role="dependent", relationship_to_subscriber="spouse", date_of_birth="1980-01-01")],
        coverage_rules=[
            CoverageRule(cpt_code="97161", is_covered=True, requires_preauth=False, allowed_amount=18000.0, copay=0.0, deductible_applies=True)
        ]
    )

    service._policies["PLAN-A"] = policy_a
    service._policies["PLAN-B"] = policy_b

    engine = COBEngine(service)

    claim = Claim(
        claim_id="INV-CLAIM-1",
        member_id="M-101",
        lines=[ClaimLine(cpt_code="97161", billed_amount=20000.0)],
        diagnoses=["M54.50"]
    )

    decision = engine.coordinate_benefits(claim)

    assert len(decision.lines_coverage) == 1
    line = decision.lines_coverage[0]

    # Verify line-level conservation
    pri_paid = line.primary_coverage.primary_paid
    sec_paid = line.secondary_coverage.secondary_paid
    pat_resp = line.remaining_balance.patient_responsibility
    writeoff = line.primary_coverage.contractual_writeoff
    billed = line.billed_amount

    assert round(pri_paid + sec_paid + pat_resp + writeoff, 2) == round(billed, 2)
    assert writeoff == 5000.0  # 20000 - 15000 allowed
    assert line.primary_coverage.copay_applied == 1000.0


def test_oop_maximum_capping_and_secondary_coordination():
    """Verify that patient responsibility never exceeds remaining out-of-pocket maximum."""
    service = InsuranceService()
    service._policies.clear()

    policy = InsurancePolicy(
        policy_id="PLAN-OOP",
        provider_name="High Deductible Plan",
        group_number="GRP-OOP",
        deductible=Deductible(individual=50000.0, family=100000.0, remaining_individual=50000.0, remaining_family=100000.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=25000.0,
        remaining_out_of_pocket_max=15000.0,  # Only 15,000 left before 100% plan coverage
        members=[Member(member_id="M-OOP", first_name="Jane", last_name="Smith", role="subscriber", relationship_to_subscriber="self", date_of_birth="1990-05-15")],
        coverage_rules=[CoverageRule(cpt_code="29881", is_covered=True, requires_preauth=False)]
    )

    service._policies["PLAN-OOP"] = policy
    engine = COBEngine(service)

    claim = Claim(
        claim_id="OOP-CLAIM-1",
        member_id="M-OOP",
        lines=[ClaimLine(cpt_code="29881", billed_amount=100000.0)],
        diagnoses=["M23.231"]
    )

    decision = engine.coordinate_benefits(claim)
    assert decision.total_patient_responsibility == 15000.0
    assert decision.total_primary_paid == 85000.0
    assert round(decision.total_primary_paid + decision.total_patient_responsibility, 2) == 100000.0

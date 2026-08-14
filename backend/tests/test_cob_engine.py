import pytest
from app.schemas.insurance_engine import InsurancePolicy, Member, Deductible, Coinsurance, CoverageRule
from app.schemas.cob_engine import Claim, ClaimLine, COBDecision
from services.insurance_engine import InsuranceService
from services.cob_engine import COBEngine


@pytest.fixture
def mock_insurance_service():
    """Initializes the standard InsuranceService loading Plan A and Plan B mock JSONs."""
    return InsuranceService()


@pytest.fixture
def cob_engine(mock_insurance_service):
    """Initializes the COBEngine with the loaded insurance service."""
    return COBEngine(mock_insurance_service)


def test_payment_order_priya(cob_engine):
    """Verify that Priya Sen's dual coverage resolves with BlueShield as primary (subscriber) and UnitedHealth as secondary (dependent)."""
    # Priya Sen is Member 98765
    patient_member = cob_engine.insurance_service.get_member("98765")
    assert patient_member is not None

    # Load matched policies
    matched_policies = [
        cob_engine.insurance_service._policies["BS-120-BLUE"],
        cob_engine.insurance_service._policies["UH-990-GOLD"],
    ]

    primary, secondary = cob_engine.determine_payment_order(patient_member, matched_policies)
    assert primary is not None
    assert secondary is not None
    assert primary.policy_id == "BS-120-BLUE"
    assert secondary.policy_id == "UH-990-GOLD"


def test_payment_order_aarav(cob_engine):
    """Verify that Aarav Sen's dual coverage resolves with BlueShield as primary and UnitedHealth as secondary via the Birthday Rule."""
    # Aarav Sen is Member 98765-02
    patient_member = cob_engine.insurance_service.get_member("98765-02")
    assert patient_member is not None

    matched_policies = [
        cob_engine.insurance_service._policies["BS-120-BLUE"],
        cob_engine.insurance_service._policies["UH-990-GOLD"],
    ]

    primary, secondary = cob_engine.determine_payment_order(patient_member, matched_policies)
    assert primary is not None
    assert secondary is not None
    assert primary.policy_id == "BS-120-BLUE"  # Priya's birthday (April 12) is earlier than Dev's (June 20)
    assert secondary.policy_id == "UH-990-GOLD"


def test_coordinate_benefits_priya_pt(cob_engine):
    """Verify full financial coordination for Priya Sen's physical therapy claim."""
    # Claim for Priya Sen (98765)
    # Physical Therapy Eval CPT 97161. Billed charge: ₹20000.00
    # Setup fresh deductibles in a separate service instance to prevent test cross-pollution
    service = InsuranceService()
    engine = COBEngine(service)

    # Verify initial deductible balances
    policy_a = service._policies["BS-120-BLUE"]
    policy_b = service._policies["UH-990-GOLD"]
    assert policy_a.deductible.remaining_individual == 20000.0
    assert policy_b.deductible.remaining_individual == 40000.0

    claim = Claim(
        claim_id="CLAIM-100",
        member_id="98765",
        lines=[ClaimLine(cpt_code="97161", billed_amount=20000.0)],
        diagnoses=["M54.50"],
    )

    decision = engine.coordinate_benefits(claim)

    assert isinstance(decision, COBDecision)
    assert decision.claim_id == "CLAIM-100"
    assert decision.patient_name == "Priya Sen"
    assert decision.primary_policy_id == "BS-120-BLUE"
    assert decision.secondary_policy_id == "UH-990-GOLD"
    assert decision.total_billed == 20000.0

    # Adjudication checks:
    # 1. Primary (BlueShield):
    #   - Billed: ₹20000.00
    #   - Deductible Applied: ₹20000.00 (remaining individual deductible)
    #   - Coinsurance Subject: ₹20000 - ₹20000 = ₹0
    #   - Coinsurance Rate: 20%
    #   - Coinsurance Amount: ₹0.00
    #   - Primary Paid: ₹0.00
    #   - Primary Patient Responsibility: ₹20000.00
    line_cov = decision.lines_coverage[0]
    assert line_cov.primary_coverage.is_covered is True
    assert line_cov.primary_coverage.deductible_applied == 20000.0
    assert line_cov.primary_coverage.coinsurance_amount == 0.0
    assert line_cov.primary_coverage.primary_paid == 0.0
    assert line_cov.primary_coverage.patient_responsibility == 20000.0

    # 2. Secondary (UnitedHealth):
    #   - Patient responsibility after primary: ₹20000.00
    #   - Secondary remaining individual deductible: ₹40000.00
    #   - Secondary deductible applied if primary: min(20000, 40000) = ₹20000.00
    #   - Secondary coinsurance rate: 10%
    #   - Secondary normal benefit if primary: (20000 - 40000) * 0.9 = ₹0.00
    #   - Secondary paid: min(20000, 0) = ₹0.00
    #   - Secondary deductible satisfied: min(20000, 20000) = ₹20000.00
    #   - Final patient responsibility: ₹20000 - ₹0 = ₹20000.00
    assert line_cov.secondary_coverage.is_covered is True
    assert line_cov.secondary_coverage.deductible_applied == 20000.0
    assert line_cov.secondary_coverage.secondary_paid == 0.0
    assert line_cov.secondary_coverage.patient_responsibility == 20000.0

    # 3. Totals checks:
    assert decision.total_primary_paid == 0.0
    assert decision.total_secondary_paid == 0.0
    assert decision.total_patient_responsibility == 20000.0

    # 4. Check updated remaining deductibles on policy instances
    assert policy_a.deductible.remaining_individual == 0.0
    assert policy_b.deductible.remaining_individual == 20000.0  # 40000 - 20000


def test_coordinate_benefits_custom_not_covered():
    """Verify benefit coordination when a procedure is not covered by primary but covered by secondary."""
    # Build custom service and engine with in-memory policies
    service = InsuranceService()
    service._policies.clear()

    # Define Policy A (Primary, does not cover CPT 99999)
    policy_a = InsurancePolicy(
        policy_id="POLICY-A",
        provider_name="Insurer A",
        group_number="A1",
        deductible=Deductible(individual=10000.0, family=20000.0, remaining_individual=10000.0, remaining_family=20000.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=100000.0,
        remaining_out_of_pocket_max=100000.0,
        members=[
            Member(member_id="MEM-001", first_name="Jane", last_name="Doe", role="subscriber", relationship_to_subscriber="self", date_of_birth="1990-01-01")
        ],
        coverage_rules=[
            CoverageRule(cpt_code="97161", is_covered=False, requires_preauth=False)
        ]
    )

    # Define Policy B (Secondary, covers CPT 99999)
    policy_b = InsurancePolicy(
        policy_id="POLICY-B",
        provider_name="Insurer B",
        group_number="B1",
        deductible=Deductible(individual=5000.0, family=10000.0, remaining_individual=5000.0, remaining_family=10000.0),
        coinsurance=Coinsurance(rate=0.10),
        out_of_pocket_max=100000.0,
        remaining_out_of_pocket_max=100000.0,
        members=[
            Member(member_id="MEM-002", first_name="Jane", last_name="Doe", role="dependent", relationship_to_subscriber="spouse", date_of_birth="1990-01-01")
        ],
        coverage_rules=[
            CoverageRule(cpt_code="97161", is_covered=True, requires_preauth=False)
        ]
    )

    service._policies["POLICY-A"] = policy_a
    service._policies["POLICY-B"] = policy_b

    engine = COBEngine(service)

    claim = Claim(
        claim_id="CLAIM-200",
        member_id="MEM-001",
        lines=[ClaimLine(cpt_code="97161", billed_amount=20000.0)],
        diagnoses=["M54.50"],
    )

    decision = engine.coordinate_benefits(claim)

    assert decision.primary_policy_id == "POLICY-A"
    assert decision.secondary_policy_id == "POLICY-B"

    # Line item adjudication details:
    # 1. Primary (excluded):
    #   - Billed: ₹20000.00
    #   - Paid: ₹0.00
    #   - Patient Responsibility: ₹20000.00
    line_cov = decision.lines_coverage[0]
    assert line_cov.primary_coverage.is_covered is False
    assert line_cov.primary_coverage.primary_paid == 0.0
    assert line_cov.primary_coverage.patient_responsibility == 20000.0

    # 2. Secondary (covered, processes as primary since primary excluded it):
    #   - Billed: ₹20000.00
    #   - Deductible Applied: ₹5000.00
    #   - Coinsurance Subject: ₹15000.00
    #   - Coinsurance rate: 10% (₹1500.00 coinsurance)
    #   - Paid: ₹13500.00
    #   - Patient Responsibility: ₹5000 + ₹1500 = ₹6500.00
    assert line_cov.secondary_coverage.is_covered is True
    assert line_cov.secondary_coverage.deductible_applied == 5000.0
    assert line_cov.secondary_coverage.secondary_paid == 13500.0
    assert line_cov.secondary_coverage.patient_responsibility == 6500.0

    assert decision.total_primary_paid == 0.0
    assert decision.total_secondary_paid == 13500.0
    assert decision.total_patient_responsibility == 6500.0


def test_medical_necessity_checking(cob_engine):
    """Verify that CPT 29888 and 29881 are denied when diagnoses do not support them, and approved when they do."""
    service = InsuranceService()
    engine = COBEngine(service)

    # Scenario 1: Normal knee MRI report (Z04.89), no ACL or meniscus tear diagnoses
    claim_denied = Claim(
        claim_id="CLAIM-DENIED",
        member_id="98765-02",  # Aarav Sen
        lines=[
            ClaimLine(cpt_code="29888", billed_amount=350000.0),
            ClaimLine(cpt_code="29881", billed_amount=100000.0),
            ClaimLine(cpt_code="73721", billed_amount=12000.0),
        ],
        diagnoses=["Z04.89"]
    )

    decision_denied = engine.coordinate_benefits(claim_denied)

    # 29888 and 29881 should be denied
    line_29888 = next(l for l in decision_denied.lines_coverage if l.cpt_code == "29888")
    assert line_29888.primary_coverage.is_covered is False
    assert line_29888.secondary_coverage.is_covered is False
    assert line_29888.remaining_balance.primary_paid == 0.0
    assert line_29888.remaining_balance.secondary_paid == 0.0
    assert line_29888.remaining_balance.patient_responsibility == 350000.0
    assert "not medically necessary" in line_29888.remaining_balance.notes.lower()

    line_29881 = next(l for l in decision_denied.lines_coverage if l.cpt_code == "29881")
    assert line_29881.primary_coverage.is_covered is False
    assert line_29881.secondary_coverage.is_covered is False
    assert "not medically necessary" in line_29881.remaining_balance.notes.lower()

    # 73721 (MRI) should be covered
    line_73721 = next(l for l in decision_denied.lines_coverage if l.cpt_code == "73721")
    assert line_73721.primary_coverage.is_covered is True

    # Scenario 2: Diagnoses support the surgery (S83.511A for ACL tear, M23.231 for meniscus tear)
    claim_approved = Claim(
        claim_id="CLAIM-APPROVED",
        member_id="98765-02",  # Aarav Sen
        lines=[
            ClaimLine(cpt_code="29888", billed_amount=350000.0),
            ClaimLine(cpt_code="29881", billed_amount=100000.0),
        ],
        diagnoses=["S83.511A", "M23.231"]
    )

    decision_approved = engine.coordinate_benefits(claim_approved)
    
    line_29888_app = next(l for l in decision_approved.lines_coverage if l.cpt_code == "29888")
    assert line_29888_app.primary_coverage.is_covered is True
    assert line_29888_app.remaining_balance.primary_paid > 0.0

    line_29881_app = next(l for l in decision_approved.lines_coverage if l.cpt_code == "29881")
    assert line_29881_app.primary_coverage.is_covered is True
    assert line_29881_app.remaining_balance.primary_paid > 0.0

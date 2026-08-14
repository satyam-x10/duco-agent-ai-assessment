import pytest
from app.core.adk import SharedWorkflowState
from services.audio import AudioBriefingService
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from app.schemas.insurance_engine import InsurancePolicy, Member, CoverageRule, Deductible, Coinsurance
from app.schemas.cob_engine import COBDecision
from app.schemas.finance_engine import FinancialReport, CostSummary, PatientResponsibility, FinancialBreakdown


@pytest.fixture
def briefing_service():
    return AudioBriefingService()


def test_audio_briefing_generation_priya(briefing_service):
    """Verify that AudioBriefingService generates a correct, structured patient narration for Priya (PT scenario)."""
    state = SharedWorkflowState(claim_id="CLAIM-PT-123", member_id="98765")
    
    # Setup mock codes
    state.coding_result = CodingResult(
        diagnoses=[
            Diagnosis(code="M23.231", description="Complete tear of medial meniscus, right knee", confidence=0.95),
        ],
        procedures=[
            Procedure(code="97161", description="Physical therapy evaluation", confidence=0.94),
        ]
    )

    # Setup mock policies
    state.primary_policy = InsurancePolicy(
        policy_id="BS-120-BLUE",
        provider_name="BlueShield Cross",
        group_number="BS120",
        deductible=Deductible(individual=500.0, family=1000.0, remaining_individual=200.0, remaining_family=500.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=3000.0,
        remaining_out_of_pocket_max=1200.0,
        members=[
            Member(member_id="98765", first_name="Priya", last_name="Sen", role="subscriber", relationship_to_subscriber="self", date_of_birth="1985-04-12")
        ],
        coverage_rules=[
            CoverageRule(cpt_code="97161", is_covered=True, requires_preauth=False)
        ]
    )

    state.financial_report = FinancialReport(
        report_id="REP-PT-123",
        claim_id=state.claim_id,
        patient_name="Priya Sen",
        breakdown=FinancialBreakdown(
            allocations=[],
            patient_responsibility=PatientResponsibility(
                total_deductible=0.0,
                total_coinsurance=65.0,
                total_responsibility=65.0,
                explanation_notes="Coordinated patient responsibility is ₹65.00."
            ),
            summary=CostSummary(
                total_billed=650.0,
                total_primary_paid=360.0,
                total_secondary_paid=225.0,
                total_insurer_paid=585.0,
                total_patient_responsibility=65.0,
                total_savings=585.0
            )
        ),
        generated_at="2026-06-25T12:00:00Z"
    )

    response = briefing_service.generate_briefing(state)
    assert response.claim_id == "CLAIM-PT-123"
    
    briefing = response.briefing
    assert briefing.patient_name == "Priya Sen"
    assert len(briefing.sections) == 6
    
    # Assert section titles
    section_titles = [sec.title for sec in briefing.sections]
    assert "Greeting" in section_titles
    assert "Summary" in section_titles
    assert "Insurance" in section_titles
    assert "Financial Summary" in section_titles
    assert "Pre-Authorization" in section_titles
    assert "Closing" in section_titles

    # Assert content details
    greeting_sec = next(s for s in briefing.sections if s.title == "Greeting")
    assert "Hello Priya" in greeting_sec.text

    financial_sec = next(s for s in briefing.sections if s.title == "Financial Summary")
    assert "65.00" in financial_sec.text  # Confirm patient responsibility amount
    assert "650.00" in financial_sec.text  # Confirm billed amount

    preauth_sec = next(s for s in briefing.sections if s.title == "Pre-Authorization")
    assert "not required" in preauth_sec.text.lower()  # Prior auth is not required for PT 97161

    # Assert word count and duration bounds
    assert briefing.estimated_duration_seconds > 0.0
    assert len(briefing.full_narration.split()) < 400


def test_audio_briefing_generation_aarav_surgery(briefing_service):
    """Verify that AudioBriefingService generates a correct narration for Aarav requiring prior auth."""
    state = SharedWorkflowState(claim_id="CLAIM-SURG-456", member_id="54321")
    
    state.coding_result = CodingResult(
        diagnoses=[
            Diagnosis(code="M23.231", description="Complete tear of medial meniscus, right knee", confidence=0.95),
        ],
        procedures=[
            Procedure(code="29881", description="Knee Arthroscopy Meniscectomy", confidence=0.98),
        ]
    )

    state.primary_policy = InsurancePolicy(
        policy_id="UHC-567-GOLD",
        provider_name="UnitedHealth",
        group_number="GRP1192",
        deductible=Deductible(individual=500.0, family=1000.0, remaining_individual=200.0, remaining_family=500.0),
        coinsurance=Coinsurance(rate=0.10),
        out_of_pocket_max=3000.0,
        remaining_out_of_pocket_max=1200.0,
        members=[
            Member(member_id="54321", first_name="Aarav", last_name="Sen", role="subscriber", relationship_to_subscriber="self", date_of_birth="2012-05-14")
        ],
        coverage_rules=[
            CoverageRule(cpt_code="29881", is_covered=True, requires_preauth=True)  # Requires prior authorization!
        ]
    )

    state.financial_report = FinancialReport(
        report_id="REP-SURG-456",
        claim_id=state.claim_id,
        patient_name="Aarav Sen",
        breakdown=FinancialBreakdown(
            allocations=[],
            patient_responsibility=PatientResponsibility(
                total_deductible=200.0,
                total_coinsurance=380.0,
                total_responsibility=580.0,
                explanation_notes="Patient responsibility is ₹580.00."
            ),
            summary=CostSummary(
                total_billed=8900.0,
                total_primary_paid=7120.0,
                total_secondary_paid=1200.0,
                total_insurer_paid=8320.0,
                total_patient_responsibility=580.0,
                total_savings=8320.0
            )
        ),
        generated_at="2026-06-25T12:00:00Z"
    )

    response = briefing_service.generate_briefing(state)
    briefing = response.briefing
    assert briefing.patient_name == "Aarav Sen"
    
    greeting_sec = next(s for s in briefing.sections if s.title == "Greeting")
    assert "Hello Aarav" in greeting_sec.text

    preauth_sec = next(s for s in briefing.sections if s.title == "Pre-Authorization")
    assert "prior authorization is required" in preauth_sec.text.lower()
    assert "UnitedHealth" in preauth_sec.text

    closing_sec = next(s for s in briefing.sections if s.title == "Closing")
    assert "submit the prior-authorization" in closing_sec.text.lower()

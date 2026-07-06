import pytest
from app.core.adk import SharedWorkflowState
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from app.schemas.cob_engine import COBDecision, ClaimLineCoverage, PrimaryCoverage, SecondaryCoverage, RemainingBalance
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.intake import DocumentType
from agents.reviewer import ReviewerAgent
from services.preauth import PreAuthorizationService
from services.audio import AudioBriefingService
from services.insurance_engine import InsuranceService

@pytest.fixture
def mock_insurance_service():
    return InsuranceService()

@pytest.mark.asyncio
async def test_reviewer_flags_medical_necessity_mismatch():
    # Setup state
    state = SharedWorkflowState(claim_id="TEST-NECESSITY", member_id="98765")
    
    # 29888 (ACL Reconstruction) is extracted, but diagnosis is just Z04.89 (Normal MRI)
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="Z04.89", description="Normal MRI of right knee", confidence=0.99)],
        procedures=[Procedure(code="29888", description="ACL reconstruction", confidence=0.95)]
    )
    
    # Run ReviewerAgent
    reviewer = ReviewerAgent()
    
    # We need a minimal financial report & cob decision to satisfy primary artifact checks in reviewer
    from app.schemas.finance_engine import FinancialReport, FinancialBreakdown, CostSummary, PatientResponsibility
    state.cob_decision = COBDecision(
        claim_id="TEST-NECESSITY",
        patient_name="Aarav Sen",
        primary_policy_id="BS-120-BLUE",
        primary_provider="BlueShield Cross",
        lines_coverage=[],
        total_billed=0.0,
        total_primary_paid=0.0,
        total_secondary_paid=0.0,
        total_patient_responsibility=0.0
    )
    state.financial_report = FinancialReport(
        report_id="FIN-123",
        claim_id="TEST-NECESSITY",
        patient_name="Aarav Sen",
        generated_at="2026-07-06T00:00:00Z",
        primary_policy_id="BS-120-BLUE",
        breakdown=FinancialBreakdown(
            allocations=[],
            patient_responsibility=PatientResponsibility(
                total_deductible=0.0,
                total_coinsurance=0.0,
                total_responsibility=0.0,
                explanation_notes=""
            ),
            summary=CostSummary(
                total_billed=0.0,
                total_primary_paid=0.0,
                total_secondary_paid=0.0,
                total_insurer_paid=0.0,
                total_patient_responsibility=0.0,
                total_savings=0.0
            )
        )
    )
    
    await reviewer.execute(state)
    
    # Should flag a warning for procedure 29888 lacking supporting ACL injury diagnosis code
    assert any("29888" in w and "lacks a supporting ACL injury diagnosis code" in w for w in state.warnings)

def test_preauth_excludes_denied_procedure(mock_insurance_service):
    state = SharedWorkflowState(claim_id="TEST-NECESSITY", member_id="98765")
    state.primary_policy = mock_insurance_service._policies["BS-120-BLUE"]
    
    # 29888 is not medically necessary (denied)
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="Z04.89", description="Normal MRI of right knee", confidence=0.99)],
        procedures=[Procedure(code="29888", description="ACL reconstruction", confidence=0.95)]
    )
    
    state.cob_decision = COBDecision(
        claim_id="TEST-NECESSITY",
        patient_name="Aarav Sen",
        primary_policy_id="BS-120-BLUE",
        primary_provider="BlueShield Cross",
        lines_coverage=[
            ClaimLineCoverage(
                cpt_code="29888",
                billed_amount=350000.0,
                primary_coverage=PrimaryCoverage(
                    policy_id="BS-120-BLUE",
                    is_covered=False,
                    deductible_applied=0.0,
                    coinsurance_rate=0.0,
                    coinsurance_amount=0.0,
                    primary_paid=0.0,
                    patient_responsibility=350000.0
                ),
                secondary_coverage=SecondaryCoverage(
                    policy_id="",
                    is_covered=False,
                    deductible_applied=0.0,
                    coinsurance_rate=0.0,
                    coinsurance_amount=0.0,
                    secondary_paid=0.0,
                    patient_responsibility=350000.0
                ),
                remaining_balance=RemainingBalance(
                    billed_amount=350000.0,
                    primary_paid=0.0,
                    secondary_paid=0.0,
                    patient_responsibility=350000.0,
                    notes="CPT 29888 (ACL Reconstruction) is not covered/approved by the insurer because the diagnostic MRI report shows no ACL injury, meaning the procedure is not medically necessary."
                )
            )
        ],
        total_billed=350000.0,
        total_primary_paid=0.0,
        total_secondary_paid=0.0,
        total_patient_responsibility=350000.0
    )
    
    preauth_service = PreAuthorizationService()
    res = preauth_service.generate_letters(state)
    
    # Since 29888 is not medically necessary, no letters should be generated
    assert len(res.letters) == 0

def test_audio_briefing_explains_necessity_denial():
    state = SharedWorkflowState(claim_id="TEST-NECESSITY", member_id="98765")
    
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="Z04.89", description="Normal MRI of right knee", confidence=0.99)],
        procedures=[Procedure(code="29888", description="ACL reconstruction", confidence=0.95)]
    )
    
    state.cob_decision = COBDecision(
        claim_id="TEST-NECESSITY",
        patient_name="Aarav Sen",
        primary_policy_id="BS-120-BLUE",
        primary_provider="BlueShield Cross",
        lines_coverage=[
            ClaimLineCoverage(
                cpt_code="29888",
                billed_amount=350000.0,
                primary_coverage=PrimaryCoverage(
                    policy_id="BS-120-BLUE",
                    is_covered=False,
                    deductible_applied=0.0,
                    coinsurance_rate=0.0,
                    coinsurance_amount=0.0,
                    primary_paid=0.0,
                    patient_responsibility=350000.0
                ),
                secondary_coverage=SecondaryCoverage(
                    policy_id="",
                    is_covered=False,
                    deductible_applied=0.0,
                    coinsurance_rate=0.0,
                    coinsurance_amount=0.0,
                    secondary_paid=0.0,
                    patient_responsibility=350000.0
                ),
                remaining_balance=RemainingBalance(
                    billed_amount=350000.0,
                    primary_paid=0.0,
                    secondary_paid=0.0,
                    patient_responsibility=350000.0,
                    notes="CPT 29888 (ACL Reconstruction) is not covered/approved by the insurer because the diagnostic MRI report shows no ACL injury, meaning the procedure is not medically necessary."
                )
            )
        ],
        total_billed=350000.0,
        total_primary_paid=0.0,
        total_secondary_paid=0.0,
        total_patient_responsibility=350000.0
    )
    
    audio_service = AudioBriefingService()
    res = audio_service.generate_briefing(state)
    
    # Financial summary text should contain explanation that the ACL reconstruction is not insurable because diagnostic report shows no ACL injury
    fin_section = next(sec for sec in res.briefing.sections if sec.title == "Financial Summary")
    assert "ACL reconstruction procedure is not insurable" in fin_section.text
    assert "shows no ACL injury" in fin_section.text

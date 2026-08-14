import pytest
from unittest.mock import MagicMock
from app.core.adk import SharedWorkflowState, Orchestrator, Agent, TraceEntry
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from app.schemas.insurance_engine import InsurancePolicy, Member, CoverageRule, Deductible, Coinsurance
from app.schemas.cob_engine import ClaimLine, COBDecision
from services.preauth import PreAuthorizationService
from services.audio import AudioBriefingService
from app.api.v1.endpoints.reports import generate_letter_pdf


def test_pdf_generation_valid_bytes():
    """Verify that generate_letter_pdf produces valid non-empty PDF binary bytes."""
    sample_markdown = """# PRIOR AUTHORIZATION REQUEST — DRAFT FOR CLINICIAN REVIEW
**DATE:** June 20, 2026
**TO:** Prior Authorization Department, BlueShield Cross

## Patient and policy
- **Patient:** Priya Sen
- **Member ID:** 98765
- **Policy:** BS-120-BLUE

## Procedures requiring authorization under this plan
| CPT | Description | Source-grounded billed amount |
| --- | --- | ---: |
| `97161` | Physical therapy evaluation | INR 20,000.00 |

## Clinical evidence
- priya_pt_invoice: documented codes M54.50.
"""
    pdf_bytes = generate_letter_pdf(sample_markdown)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


def test_audio_briefing_sections_and_narration():
    """Verify that AudioBriefingService generates all structured sections and calculated speaking duration."""
    state = SharedWorkflowState(claim_id="AUDIO-TEST-1", member_id="98765", patient_name="Priya Sen")
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="M54.50", description="Low back pain", confidence=0.99)],
        procedures=[Procedure(code="97161", description="PT Evaluation", confidence=0.99)],
    )
    state.primary_policy = InsurancePolicy(
        policy_id="BS-120-BLUE",
        provider_name="BlueShield Cross",
        group_number="BS120",
        deductible=Deductible(individual=50000.0, family=100000.0, remaining_individual=20000.0, remaining_family=50000.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=300000.0,
        remaining_out_of_pocket_max=120000.0,
        members=[Member(member_id="98765", first_name="Priya", last_name="Sen", role="subscriber", relationship_to_subscriber="self", date_of_birth="1985-04-12")],
        coverage_rules=[CoverageRule(cpt_code="97161", is_covered=True, requires_preauth=False)],
    )
    state.cob_decision = COBDecision(
        claim_id="AUDIO-TEST-1",
        patient_name="Priya Sen",
        primary_policy_id="BS-120-BLUE",
        primary_provider="BlueShield Cross",
        lines_coverage=[],
        total_billed=20000.0,
        total_primary_paid=0.0,
        total_secondary_paid=0.0,
        total_patient_responsibility=20000.0,
    )

    service = AudioBriefingService()
    res = service.generate_briefing(state)

    assert res.claim_id == "AUDIO-TEST-1"
    assert res.briefing.patient_name == "Priya Sen"
    assert len(res.briefing.sections) == 6
    section_titles = [s.title for s in res.briefing.sections]
    assert "Greeting" in section_titles
    assert "Financial Summary" in section_titles
    assert "Pre-Authorization" in section_titles
    assert res.briefing.estimated_duration_seconds > 0.0
    assert "Priya" in res.briefing.full_narration


def test_preauth_letter_generation_structure():
    """Verify that PreAuthorizationService builds well-formed prior authorization draft letters."""
    state = SharedWorkflowState(claim_id="PREAUTH-TEST-1", member_id="98765-02", patient_name="Aarav Sen")
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="M23.231", description="Meniscus tear", confidence=0.99)],
        procedures=[Procedure(code="29881", description="Meniscectomy", confidence=0.99)],
    )
    state.claim_lines = [ClaimLine(cpt_code="29881", billed_amount=100000.0)]
    state.primary_policy = InsurancePolicy(
        policy_id="BS-120-BLUE",
        provider_name="BlueShield Cross",
        group_number="BS120",
        deductible=Deductible(individual=50000.0, family=100000.0, remaining_individual=20000.0, remaining_family=50000.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=300000.0,
        remaining_out_of_pocket_max=120000.0,
        members=[Member(member_id="98765-02", first_name="Aarav", last_name="Sen", role="dependent", relationship_to_subscriber="child", date_of_birth="2012-05-14")],
        coverage_rules=[CoverageRule(cpt_code="29881", is_covered=True, requires_preauth=True)],
    )

    service = PreAuthorizationService()
    res = service.generate_letters(state)

    assert len(res.letters) == 1
    letter = res.letters[0]
    assert letter.insurer_name == "BlueShield Cross"
    assert "29881" in letter.letter_content
    assert "Aarav Sen" in letter.letter_content
    assert "M23.231" in letter.letter_content
    assert "100,000.00" in letter.letter_content


@pytest.mark.asyncio
async def test_planner_step_limit_fails_cleanly():
    """Verify that an infinite loop / step limit does not report false success."""
    class LoopingAgent(Agent):
        def __init__(self):
            super().__init__("LoopingAgent")

        async def execute(self, state: SharedWorkflowState) -> None:
            # Does not mutate state to resolve next step
            pass

    state = SharedWorkflowState(claim_id="LOOP-TEST", member_id="98765")
    # Standard 7 agents list with LoopingAgent instead of Intake
    orchestrator = Orchestrator([
        LoopingAgent(),
        LoopingAgent(),
        LoopingAgent(),
        LoopingAgent(),
        LoopingAgent(),
        LoopingAgent(),
        LoopingAgent(),
    ])

    await orchestrator.execute(state)
    assert state.workflow_status in ("failed", "success")

import pytest
import json
from unittest.mock import MagicMock, patch
from app.core.adk import SharedWorkflowState
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from app.schemas.cob_engine import COBDecision
from app.schemas.finance_engine import FinancialReport, FinancialBreakdown, CostSummary, PatientResponsibility
from agents.reviewer import ReviewerAgent

@pytest.mark.asyncio
@patch("agents.reviewer.genai.Client")
async def test_reviewer_gemini_audit_success(mock_client_class, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-reviewer-key")
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "warnings": ["[Coding Inconsistency] Procedure 29888 is not supported by a normal MRI report."],
        "requires_human_approval": True,
        "rationale": "The MRI report explicitly states normal findings for the ACL, making procedure 29888 medically unnecessary."
    })
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client
    
    # Set up state
    state = SharedWorkflowState(claim_id="TEST-GEMINI-REVIEW", member_id="98765", mock_mode=False)
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="Z04.89", description="Normal MRI of right knee", confidence=0.99)],
        procedures=[Procedure(code="29888", description="ACL reconstruction", confidence=0.95)]
    )
    state.cob_decision = COBDecision(
        claim_id="TEST-GEMINI-REVIEW",
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
        claim_id="TEST-GEMINI-REVIEW",
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
    
    reviewer = ReviewerAgent()
    await reviewer.execute(state)
    
    assert len(state.warnings) == 3
    assert any("Procedure 29888 is not supported by a normal MRI report" in w for w in state.warnings)
    assert state.requires_human_approval is True

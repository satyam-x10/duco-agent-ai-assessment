import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.adk import Agent, SharedWorkflowState, Orchestrator, TraceEntry
from app.schemas.intake import DocumentType, DocumentMetadata
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from services.storage import LocalStorageService
from app.dependencies.document_intelligence import get_doc_intel_service
from services.medical_coding import MedicalCodingService
from services.insurance_engine import InsuranceService
from services.cob_engine import COBEngine
from services.finance_engine import FinanceEngine

from agents.intake import IntakeAgent
from agents.document_intelligence import DocIntelAgent
from agents.medical_coding import MedicalCodingAgent
from agents.insurance import InsuranceAgent
from agents.cob import COBAgent
from agents.finance import FinanceAgent
from agents.reviewer import ReviewerAgent


# 1. Dummy/Mock Failure Agent for retry tests
class FailureAgent(Agent):
    def __init__(self):
        super().__init__("FailureAgent")
        self.attempts = 0

    async def execute(self, state: SharedWorkflowState) -> None:
        self.attempts += 1
        raise ValueError(f"Simulated failure attempt {self.attempts}")


@pytest.mark.asyncio
async def test_orchestrator_retry_and_failure_propagation():
    """Verify that Orchestrator executes retries up to max limit and then propagates error."""
    fail_agent = FailureAgent()
    orchestrator = Orchestrator([fail_agent])
    
    state = SharedWorkflowState(claim_id="CLAIM-FAIL", member_id="98765")
    
    with pytest.raises(RuntimeError) as exc_info:
        await orchestrator.execute(state, max_retries=2)
        
    assert "failed after 3 attempts" in str(exc_info.value)
    assert fail_agent.attempts == 3
    
    # Check trace entries
    retries = [t for t in state.trace if t.status == "retry"]
    errors = [t for t in state.trace if t.status == "error"]
    assert len(retries) == 2
    assert len(errors) == 1
    assert "FailureAgent" in state.errors[0]


@pytest.mark.asyncio
async def test_reviewer_agent_low_confidence():
    """Verify that ReviewerAgent catches and logs warnings for low-confidence coding results."""
    reviewer = ReviewerAgent()
    state = SharedWorkflowState(claim_id="CLAIM-REV", member_id="98765")
    
    # Add a mock financial report and COB decision to pass structural checks
    state.cob_decision = MagicMock()
    state.financial_report = MagicMock()
    state.financial_report.patient_name = "Priya Sen"
    state.financial_report.primary_policy_id = "BS-120-BLUE"
    state.financial_report.secondary_policy_id = "UH-990-GOLD"
    
    # Inject a low-confidence diagnosis code (< 0.70)
    state.coding_result = CodingResult(
        diagnoses=[
            Diagnosis(code="M23.231", description="Tear of meniscus", confidence=0.50)
        ],
        procedures=[
            Procedure(code="29881", description="Meniscus repair", confidence=0.90)
        ]
    )
    
    await reviewer.execute(state)
    
    assert len(state.warnings) >= 1
    assert any("Low confidence diagnosis code" in w for w in state.warnings)


@pytest.mark.asyncio
@patch("services.medical_coding.genai.Client")
async def test_end_to_end_orchestration_pipeline(mock_client_class, tmp_path):
    """Verify end-to-end multi-agent execution sequencing and state mutation using mock services."""
    import json
    
    # Mock Gemini API Response for Medical Coding
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "diagnoses": [
            {"code": "M23.231", "description": "Tear of medial meniscus", "confidence": 0.96}
        ],
        "procedures": [
            {"code": "97161", "description": "Physical therapy evaluation", "confidence": 0.98}
        ]
    })
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    # Write mock files on disk to pass Path.exists() check
    invoice_path = tmp_path / "invoice.txt"
    invoice_path.write_text("Patient Name: Priya Sen\nProcedure code is 97161. Total PT Evaluation.")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("Patient Name: Priya Sen\nSubscriber is Priya Sen under BS-120-BLUE.")

    # Setup fresh service instances
    storage_service = LocalStorageService()
    doc_intel_service = get_doc_intel_service()
    medical_coding_service = MedicalCodingService()
    insurance_service = InsuranceService()
    cob_engine = COBEngine(insurance_service)
    finance_engine = FinanceEngine()

    # Mock get_status to return ready documents
    mock_meta_pt = DocumentMetadata(
        filename="invoice.txt",
        size_bytes=100,
        content_type="text/plain",
        upload_time="2026-06-25T12:00:00Z",
        status="ready"
    )
    mock_meta_transcript = DocumentMetadata(
        filename="transcript.txt",
        size_bytes=100,
        content_type="text/plain",
        upload_time="2026-06-25T12:00:00Z",
        status="ready"
    )
    
    # Patch storage status to return simulated ready claims documents
    storage_service.get_status = AsyncMock(return_value={
        DocumentType.PRIYA_PT_INVOICE: mock_meta_pt,
        DocumentType.USER_QUERY_TRANSCRIPT: mock_meta_transcript,
        DocumentType.AARAV_MRI_REPORT: None,
        DocumentType.SURGEON_ESTIMATE: None
    })
    
    # Patch get_file_path to return real existing file Paths
    def mock_get_file_path(doc_type):
        if doc_type == DocumentType.PRIYA_PT_INVOICE:
            return invoice_path
        return transcript_path

    storage_service.get_file_path = AsyncMock(side_effect=mock_get_file_path)
    
    # Build Orchestrator
    intake_agent = IntakeAgent(storage_service)
    doc_intel_agent = DocIntelAgent(doc_intel_service, storage_service)
    medical_coding_agent = MedicalCodingAgent(medical_coding_service)
    insurance_agent = InsuranceAgent(insurance_service)
    cob_agent = COBAgent(cob_engine)
    finance_agent = FinanceAgent(finance_engine)
    reviewer_agent = ReviewerAgent()
    
    orchestrator = Orchestrator([
        intake_agent,
        doc_intel_agent,
        medical_coding_agent,
        insurance_agent,
        cob_agent,
        finance_agent,
        reviewer_agent
    ])
    
    # Patient Priya Sen has member ID 98765
    state = SharedWorkflowState(claim_id="CLAIM-12345", member_id="98765")
    
    # Run the pipeline
    await orchestrator.execute(state, max_retries=1)
    
    # Verify complete pipeline mutations
    assert len(state.errors) == 0
    assert len(state.trace) == 7  # All 7 agents successfully recorded trace entries
    assert all(t.status == "success" for t in state.trace)
    
    # Verify Doc Intel outputs
    assert DocumentType.PRIYA_PT_INVOICE in state.processed_documents
    assert DocumentType.USER_QUERY_TRANSCRIPT in state.processed_documents
    
    # Verify Medical Coding outputs
    assert state.coding_result is not None
    assert len(state.coding_result.procedures) > 0
    
    # Verify Insurance outputs
    assert state.primary_policy is not None
    assert state.primary_policy.policy_id == "BS-120-BLUE"
    assert state.secondary_policy is not None
    assert state.secondary_policy.policy_id == "UH-990-GOLD"
    
    # Verify COB outputs
    assert state.cob_decision is not None
    assert state.cob_decision.total_billed > 0.0
    
    # Verify Finance outputs
    assert state.financial_report is not None
    assert state.financial_report.breakdown.summary.total_patient_responsibility > 0.0
    
    # Verify warnings (since secondary is resolved, should not warn about single coverage note)
    assert not any("single coverage" in w for w in state.warnings)

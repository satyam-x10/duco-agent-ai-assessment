import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.adk import SharedWorkflowState, Orchestrator, TraceEntry
from app.schemas.intake import DocumentType
from app.schemas.document_intelligence import ProcessedDocument
from services.document_facts import extract_document_facts
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from app.schemas.insurance_engine import InsurancePolicy, Member, CoverageRule, Coinsurance, Deductible
from services.preauth import PreAuthorizationService
from agents.intake import IntakeAgent
from agents.document_intelligence import DocIntelAgent
from agents.medical_coding import MedicalCodingAgent
from agents.insurance import InsuranceAgent
from agents.cob import COBAgent
from agents.finance import FinanceAgent
from agents.reviewer import ReviewerAgent


# Lightweight helper to construct mock policies
def create_mock_policy(policy_id, provider_name, first_name, last_name, member_id, requires_preauth=False):
    return InsurancePolicy(
        policy_id=policy_id,
        provider_name=provider_name,
        group_number="GP123",
        deductible=Deductible(individual=500.0, family=1000.0, remaining_individual=200.0, remaining_family=500.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=3000.0,
        remaining_out_of_pocket_max=1200.0,
        members=[
            Member(
                member_id=member_id,
                first_name=first_name,
                last_name=last_name,
                role="subscriber",
                relationship_to_subscriber="self",
                date_of_birth="1985-04-12"
            )
        ],
        coverage_rules=[
            CoverageRule(cpt_code="97161", is_covered=True, requires_preauth=requires_preauth)
        ]
    )


@pytest.mark.asyncio
async def test_rule1_low_ocr_confidence_backtracking():
    """Rule 1: If OCR confidence is low, route back to DocIntelAgent with high-fidelity strategy."""
    state = SharedWorkflowState(claim_id="CLAIM-1", member_id="98765")
    
    # 1. Mock DocIntel service to return low confidence first, then high confidence
    mock_doc_intel_service = MagicMock()
    
    # First call: returns confidence 0.90 (low)
    # Second call (high_fidelity): returns confidence 0.99
    async def process_document_mock(file_path, doc_type, strategy="standard", ocr_engine="gemini"):
        if strategy == "high_fidelity":
            return ProcessedDocument(
                document_type=doc_type,
                extracted_text="Priya Sen Medical Records CPT 97161",
                page_count=1,
                confidence=0.99,
                metadata={"strategy": "high_fidelity"}
            )
        return ProcessedDocument(
            document_type=doc_type,
            extracted_text="Priya Sen Medical Records CPT 97161",
            page_count=1,
            confidence=0.90,
            metadata={"strategy": "standard"}
        )
        
    mock_doc_intel_service.process_document = process_document_mock
    mock_storage_service = MagicMock()
    mock_storage_service.get_status = AsyncMock(return_value={
        DocumentType.USER_QUERY_TRANSCRIPT: MagicMock(status="ready")
    })
    mock_storage_service.get_file_path = AsyncMock(return_value="mock.pdf")
    
    intake_agent = IntakeAgent(mock_storage_service)
    doc_intel_agent = DocIntelAgent(mock_doc_intel_service, mock_storage_service)
    
    # Dummy list of agents
    agents = [
        intake_agent,
        doc_intel_agent,
        MagicMock(spec=MedicalCodingAgent, name="MedicalCodingAgent"),
        MagicMock(spec=InsuranceAgent, name="InsuranceAgent"),
        MagicMock(spec=COBAgent, name="COBAgent"),
        MagicMock(spec=FinanceAgent, name="FinanceAgent"),
        MagicMock(spec=ReviewerAgent, name="ReviewerAgent"),
    ]
    for agent in agents[2:]:
        agent.name = agent._mock_name
        
    orchestrator = Orchestrator(agents)
    completed_agents = set()
    
    # Step 1: Intake runs
    next_agent, reason = orchestrator._evaluate_next_step(state, completed_agents)
    assert next_agent == "IntakeAgent"
    await intake_agent.execute(state)
    completed_agents.add("IntakeAgent")
    state.trace.append(TraceEntry(agent_name="IntakeAgent", status="success", message="Success"))
    
    # Step 2: DocIntel runs with standard strategy (returns confidence 0.90)
    next_agent, reason = orchestrator._evaluate_next_step(state, completed_agents)
    assert next_agent == "DocIntelAgent"
    await doc_intel_agent.execute(state)
    completed_agents.add("DocIntelAgent")
    state.trace.append(TraceEntry(agent_name="DocIntelAgent", status="success", message="Success"))
    
    # Step 3: Planner evaluates. It should detect low confidence (<0.95), pop the doc, and backtrack!
    next_agent, reason = orchestrator._evaluate_next_step(state, completed_agents)
    assert next_agent == "DocIntelAgent"
    assert "high-fidelity" in reason
    assert "DocIntelAgent" not in completed_agents
    assert DocumentType.USER_QUERY_TRANSCRIPT not in state.processed_documents
    assert state.ocr_strategies[DocumentType.USER_QUERY_TRANSCRIPT] == "high_fidelity"
    
    # Step 4: Run DocIntel again (this time it runs with high_fidelity)
    await doc_intel_agent.execute(state)
    completed_agents.add("DocIntelAgent")
    state.trace.append(TraceEntry(agent_name="DocIntelAgent", status="success", message="Success"))
    
    # Step 5: Planner evaluates again. Confidence is now 0.99, so it should proceed to MedicalCodingAgent
    next_agent, reason = orchestrator._evaluate_next_step(state, completed_agents)
    assert next_agent == "MedicalCodingAgent"


@pytest.mark.asyncio
async def test_rule2_no_diagnosis_extracted_retry_and_clarification():
    """Rule 2: If no diagnosis is extracted, retry MedicalCodingAgent once. If still empty, request clarification."""
    state = SharedWorkflowState(claim_id="CLAIM-2", member_id="98765")
    
    # Mock documents parsed
    state.processed_documents[DocumentType.USER_QUERY_TRANSCRIPT] = ProcessedDocument(
        document_type=DocumentType.USER_QUERY_TRANSCRIPT,
        extracted_text="Priya Sen Medical Records",
        page_count=1,
        confidence=1.0
    )
    
    completed_agents = {"IntakeAgent", "DocIntelAgent"}
    
    # MedicalCodingAgent mock
    mock_mc_service = MagicMock()
    mock_mc_service.analyze_document = AsyncMock(return_value=CodingResult(diagnoses=[], procedures=[Procedure(code="97161", description="PT", confidence=0.99)]))
    coding_agent = MedicalCodingAgent(mock_mc_service)
    
    agents = [
        MagicMock(spec=IntakeAgent, name="IntakeAgent"),
        MagicMock(spec=DocIntelAgent, name="DocIntelAgent"),
        coding_agent,
        MagicMock(spec=InsuranceAgent, name="InsuranceAgent"),
        MagicMock(spec=COBAgent, name="COBAgent"),
        MagicMock(spec=FinanceAgent, name="FinanceAgent"),
        MagicMock(spec=ReviewerAgent, name="ReviewerAgent"),
    ]
    for agent in agents:
        if agent is not coding_agent:
            agent.name = agent._mock_name
            
    orchestrator = Orchestrator(agents)
    
    # 1. Run coding agent first time (returns empty diagnoses)
    next_agent, reason = orchestrator._evaluate_next_step(state, completed_agents)
    assert next_agent == "MedicalCodingAgent"
    await coding_agent.execute(state)
    completed_agents.add("MedicalCodingAgent")
    state.trace.append(TraceEntry(agent_name="MedicalCodingAgent", status="success", message="Completed"))
    
    # 2. Planner evaluates: diagnoses is empty. It should discard MedicalCodingAgent and route back
    next_agent, reason = orchestrator._evaluate_next_step(state, completed_agents)
    assert next_agent == "MedicalCodingAgent"
    assert "No diagnoses were extracted" in reason
    assert "MedicalCodingAgent" not in completed_agents
    assert state.coding_result is None
    
    # 3. Run coding agent second time (still empty diagnoses)
    await coding_agent.execute(state)
    completed_agents.add("MedicalCodingAgent")
    state.trace.append(TraceEntry(agent_name="MedicalCodingAgent", status="success", message="Completed Retry"))
    
    # 4. Planner evaluates: already ran twice. It should halt and request human approval/clarification
    next_agent, reason = orchestrator._evaluate_next_step(state, completed_agents)
    assert next_agent is None
    assert state.requires_human_approval is True
    assert "Halting pipeline for manual clinician clarification" in reason


@pytest.mark.asyncio
async def test_rule3_bypass_cob_agent_single_policy():
    """Rule 3: If only one insurance policy exists, bypass COBAgent execution but calculate benefits."""
    state = SharedWorkflowState(claim_id="CLAIM-3", member_id="98765")
    
    state.processed_documents[DocumentType.USER_QUERY_TRANSCRIPT] = ProcessedDocument(
        document_type=DocumentType.USER_QUERY_TRANSCRIPT,
        extracted_text="Patient Name: Priya Sen\nMember ID: 98765\nICD-10 M23.231\nCPT 97161 - INR 500.00",
        page_count=1,
        confidence=1.0,
        facts=extract_document_facts("Patient Name: Priya Sen\nMember ID: 98765\nICD-10 M23.231\nCPT 97161 - INR 500.00"),
    )
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="M23.231", description="Meniscus tear", confidence=0.99)],
        procedures=[Procedure(code="97161", description="PT", confidence=0.99)]
    )
    
    # Single policy resolved
    state.primary_policy = create_mock_policy("BS-120-BLUE", "BlueShield Cross", "Priya", "Sen", "98765")
    state.secondary_policy = None
    
    completed_agents = {"IntakeAgent", "DocIntelAgent", "MedicalCodingAgent", "InsuranceAgent"}
    
    # Setup mock services and COBAgent
    mock_insurance_service = MagicMock()
    mock_insurance_service.get_member = MagicMock(return_value=state.primary_policy.members[0])
    mock_insurance_service._policies = {"BS-120-BLUE": state.primary_policy}
    mock_insurance_service.get_coverage_rule = MagicMock(
        side_effect=lambda policy, code: next((r for r in policy.coverage_rules if r.cpt_code == code), None)
    )
    mock_insurance_service.get_accumulator = MagicMock(return_value={
        "remaining_individual_deductible": 200.0,
        "remaining_out_of_pocket_max": 1200.0,
    })
    mock_insurance_service.update_accumulator = MagicMock()
    mock_insurance_service._family_deductibles = {"BS-120-BLUE": 500.0}
    
    from services.cob_engine import COBEngine
    cob_engine = COBEngine(mock_insurance_service)
    cob_agent = COBAgent(cob_engine)
    
    agents = [
        MagicMock(spec=IntakeAgent, name="IntakeAgent"),
        MagicMock(spec=DocIntelAgent, name="DocIntelAgent"),
        MagicMock(spec=MedicalCodingAgent, name="MedicalCodingAgent"),
        MagicMock(spec=InsuranceAgent, name="InsuranceAgent"),
        cob_agent,
        MagicMock(spec=FinanceAgent, name="FinanceAgent"),
        MagicMock(spec=ReviewerAgent, name="ReviewerAgent"),
    ]
    for agent in agents:
        if agent is not cob_agent:
            agent.name = agent._mock_name
            
    orchestrator = Orchestrator(agents)
    
    # Evaluate next step: COBAgent should be bypassed, cob_decision populated, and proceed directly to FinanceAgent
    next_agent, reason = orchestrator._evaluate_next_step(state, completed_agents)
    assert next_agent == "FinanceAgent"
    assert "COBAgent" in completed_agents
    assert state.cob_decision is not None
    assert state.cob_decision.primary_policy_id == "BS-120-BLUE"
    assert state.cob_decision.secondary_policy_id is None
    # Verify trace logs the bypass
    assert any("Bypassing COBAgent execution step" in t.message for t in state.trace)


def test_rule4_preauth_generator_skipping():
    """Rule 4: If no procedure requires pre-authorization under active policies, skip letter generation."""
    state = SharedWorkflowState(claim_id="CLAIM-4", member_id="98765")
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="M23.231", description="Meniscus tear", confidence=0.99)],
        procedures=[Procedure(code="97161", description="PT", confidence=0.99)]
    )
    
    # Policy has preauth = False for procedure CPT 97161
    state.primary_policy = create_mock_policy("BS-120-BLUE", "BlueShield Cross", "Priya", "Sen", "98765", requires_preauth=False)
    
    service = PreAuthorizationService()
    response = service.generate_letters(state)
    
    # Should skip and return empty letters
    assert len(response.letters) == 0


@pytest.mark.asyncio
async def test_rule5_reviewer_inconsistency_backtracking():
    """Rule 5: If ReviewerAgent detects inconsistencies, route back to MedicalCodingAgent or InsuranceAgent."""
    # CASE A: Coding Inconsistency (CPT code not covered)
    state_a = SharedWorkflowState(claim_id="CLAIM-5A", member_id="98765", mock_mode=True)
    state_a.processed_documents[DocumentType.USER_QUERY_TRANSCRIPT] = ProcessedDocument(
        document_type=DocumentType.USER_QUERY_TRANSCRIPT,
        extracted_text="Priya Sen Medical Records CPT 99999",
        page_count=1,
        confidence=1.0
    )
    state_a.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="M23.231", description="Meniscus tear", confidence=0.99)],
        procedures=[Procedure(code="99999", description="Uncovered Procedure", confidence=0.99)] # CPT 99999 is uncovered
    )
    state_a.primary_policy = create_mock_policy("BS-120-BLUE", "BlueShield Cross", "Priya", "Sen", "98765")
    # Add dummy cob_decision and financial_report
    state_a.cob_decision = MagicMock()
    state_a.financial_report = MagicMock()
    state_a.financial_report.patient_name = "Priya Sen"
    state_a.financial_report.primary_policy_id = "BS-120-BLUE"
    state_a.financial_report.secondary_policy_id = None

    reviewer = ReviewerAgent()
    await reviewer.execute(state_a)
    
    # Verify the reviewer flagged a coding inconsistency
    assert any("[Coding Inconsistency]" in w for w in state_a.warnings)
    
    # Planner evaluates with ReviewerAgent completed
    completed_agents = {"IntakeAgent", "DocIntelAgent", "MedicalCodingAgent", "InsuranceAgent", "COBAgent", "FinanceAgent", "ReviewerAgent"}
    
    agents = [
        MagicMock(spec=IntakeAgent, name="IntakeAgent"),
        MagicMock(spec=DocIntelAgent, name="DocIntelAgent"),
        MagicMock(spec=MedicalCodingAgent, name="MedicalCodingAgent"),
        MagicMock(spec=InsuranceAgent, name="InsuranceAgent"),
        MagicMock(spec=COBAgent, name="COBAgent"),
        MagicMock(spec=FinanceAgent, name="FinanceAgent"),
        reviewer
    ]
    for agent in agents[:-1]:
        agent.name = agent._mock_name
        
    orchestrator = Orchestrator(agents)
    
    # 1. Run coding agent once first
    state_a.trace.append(TraceEntry(agent_name="MedicalCodingAgent", status="success", message="Success"))
    
    # Evaluate next step: should backtrack to MedicalCodingAgent
    next_agent, reason = orchestrator._evaluate_next_step(state_a, completed_agents)
    assert next_agent == "MedicalCodingAgent"
    assert "Reviewer flagged coding inconsistency" in reason
    assert "MedicalCodingAgent" not in completed_agents
    
    # CASE B: Policy Inconsistency (Patient Name Mismatch)
    state_b = SharedWorkflowState(claim_id="CLAIM-5B", member_id="98765", mock_mode=True)
    state_b.processed_documents[DocumentType.USER_QUERY_TRANSCRIPT] = ProcessedDocument(
        document_type=DocumentType.USER_QUERY_TRANSCRIPT,
        extracted_text="John Doe Medical Records CPT 97161", # Text has 'John Doe', Policy has 'Priya Sen'
        page_count=1,
        confidence=1.0
    )
    state_b.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="M23.231", description="Meniscus tear", confidence=0.99)],
        procedures=[Procedure(code="97161", description="PT", confidence=0.99)]
    )
    state_b.primary_policy = create_mock_policy("BS-120-BLUE", "BlueShield Cross", "Priya", "Sen", "98765")
    state_b.cob_decision = MagicMock()
    state_b.financial_report = MagicMock()
    state_b.financial_report.patient_name = "Priya Sen"
    state_b.financial_report.primary_policy_id = "BS-120-BLUE"
    state_b.financial_report.secondary_policy_id = None
    
    await reviewer.execute(state_b)
    
    # Verify policy name inconsistency warning was generated
    assert any("[Policy Inconsistency]" in w for w in state_b.warnings)
    
    # Set run counts
    state_b.trace.append(TraceEntry(agent_name="InsuranceAgent", status="success", message="Success"))
    
    # Evaluate next step: should backtrack to InsuranceAgent
    completed_agents_b = {"IntakeAgent", "DocIntelAgent", "MedicalCodingAgent", "InsuranceAgent", "COBAgent", "FinanceAgent", "ReviewerAgent"}
    next_agent, reason = orchestrator._evaluate_next_step(state_b, completed_agents_b)
    assert next_agent == "InsuranceAgent"
    assert "Reviewer flagged policy inconsistency" in reason
    assert "InsuranceAgent" not in completed_agents_b

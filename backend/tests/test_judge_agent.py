import pytest
from app.core.adk import SharedWorkflowState
from agents.judge import JudgeAgent, JudgeEvaluation
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure

@pytest.mark.asyncio
async def test_judge_agent_rule_based_pass():
    agent = JudgeAgent()
    state = SharedWorkflowState(
        claim_id="TEST-001",
        member_id="MEM-12345",
        mock_mode=True,
        coding_result=CodingResult(
            diagnoses=[Diagnosis(code="M25.561", description="Pain in right knee", confidence=0.95)],
            procedures=[Procedure(code="73721", description="Knee MRI", confidence=0.95)]
        )
    )
    await agent.execute(state)
    assert state.judge_evaluation is not None
    assert state.judge_evaluation["quality_score"] >= 75.0
    assert state.judge_evaluation["passed"] is True

@pytest.mark.asyncio
async def test_judge_agent_rule_based_missing_diagnoses():
    agent = JudgeAgent()
    state = SharedWorkflowState(
        claim_id="TEST-002",
        member_id="MEM-12345",
        mock_mode=True,
        coding_result=CodingResult(
            diagnoses=[],
            procedures=[Procedure(code="73721", description="Knee MRI", confidence=0.95)]
        )
    )
    await agent.execute(state)
    assert state.judge_evaluation is not None
    assert state.judge_evaluation["passed"] is False
    assert state.judge_evaluation["target_backtrack_agent"] == "MedicalCodingAgent"

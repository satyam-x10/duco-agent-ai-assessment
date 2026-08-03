import os
import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from google import genai

from app.core.adk import Agent, SharedWorkflowState

logger = logging.getLogger(__name__)


class JudgeEvaluation(BaseModel):
    """Structured evaluation returned by the LLM-as-a-Judge validation agent."""
    quality_score: float = Field(..., description="Overall workflow state quality score from 0.0 to 100.0")
    passed: bool = Field(..., description="True if state passes all clinical, policy, and financial sanity audits")
    critique: str = Field(..., description="Detailed explanation of the verdict, findings, or identified flaws")
    recommended_action: str = Field(
        ...,
        description="Next step recommendation: APPROVED | RETRY_MEDICAL_CODING | RETRY_DOC_INTEL | RETRY_INSURANCE | HALT_FOR_HUMAN"
    )
    target_backtrack_agent: Optional[str] = Field(None, description="Name of the specialist agent to backtrack to if passed is False")
    requires_human: bool = Field(False, description="Flag indicating if immediate human auditor intervention is required")


class JudgeAgent(Agent):
    """Specialist LLM-as-a-Judge agent that evaluates overall pipeline quality and decides dynamic non-sequential retry loops."""

    def __init__(self):
        super().__init__("JudgeAgent")
        self.api_key = os.environ.get("GEMINI_API_KEY")

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"[{self.name}] Performing LLM-as-a-Judge audit on claim {state.claim_id}")

        if state.mock_mode or not self.api_key:
            logger.info(f"[{self.name}] Running deterministic rule-based judge evaluation (mock mode or no API key).")
            evaluation = self._evaluate_rule_based(state)
        else:
            try:
                evaluation = await self._evaluate_with_gemini(state)
            except Exception as e:
                logger.warning(f"[{self.name}] Gemini Judge evaluation failed ({e}). Falling back to rule-based evaluation.")
                evaluation = self._evaluate_rule_based(state)

        # Attach evaluation to state
        state.judge_evaluation = evaluation.model_dump()
        
        if not evaluation.passed:
            logger.warning(f"[{self.name}] Workflow audit REJECTED (Score {evaluation.quality_score}/100). Action: {evaluation.recommended_action}")
            if evaluation.requires_human:
                state.requires_human_approval = True
                state.workflow_status = "awaiting_approval"
        else:
            logger.info(f"[{self.name}] Workflow audit PASSED (Score {evaluation.quality_score}/100).")

    def _evaluate_rule_based(self, state: SharedWorkflowState) -> JudgeEvaluation:
        """Rule-based judge evaluation fallback."""
        score = 100.0
        reasons = []
        target_agent = None
        requires_human = False

        # 1. Missing diagnoses audit
        if state.coding_result and not state.coding_result.diagnoses:
            score -= 40.0
            reasons.append("No ICD-10 diagnosis codes were extracted from clinical documents.")
            target_agent = "MedicalCodingAgent"

        # 2. Warnings audit
        if state.warnings:
            score -= min(30.0, len(state.warnings) * 10.0)
            reasons.append(f"Audit warnings present: {'; '.join(state.warnings)}")
            if any("[Coding Inconsistency]" in w for w in state.warnings):
                target_agent = "MedicalCodingAgent"
            elif any("[Policy Inconsistency]" in w for w in state.warnings) and not target_agent:
                target_agent = "InsuranceAgent"

        # 3. Policy resolution audit
        if not state.primary_policy:
            if not target_agent:
                target_agent = "InsuranceAgent"
            if not state.coding_result:
                score -= 30.0
                reasons.append("Primary insurance policy was not resolved.")

        passed = score >= 75.0 and not state.requires_human_approval
        action = "APPROVED"
        if not passed:
            if target_agent:
                action = f"RETRY_{target_agent.upper().replace('AGENT', '')}"
            else:
                action = "HALT_FOR_HUMAN"
                requires_human = True

        critique = "State passed quality audit." if passed else " ".join(reasons)

        return JudgeEvaluation(
            quality_score=round(max(0.0, score), 1),
            passed=passed,
            critique=critique,
            recommended_action=action,
            target_backtrack_agent=target_agent,
            requires_human=requires_human or state.requires_human_approval
        )

    async def _evaluate_with_gemini(self, state: SharedWorkflowState) -> JudgeEvaluation:
        """Uses Gemini Flash model as a Judge to evaluate complete workflow state quality."""
        client = genai.Client(api_key=self.api_key)

        prompt = f"""
You are an expert healthcare claims auditor acting as an LLM-as-a-Judge for a multi-agent system.
Evaluate the following workflow state:

Claim ID: {state.claim_id}
Member ID: {state.member_id}
Diagnoses: {[d.code for d in (state.coding_result.diagnoses if state.coding_result else [])]}
Procedures: {[p.code for p in (state.coding_result.procedures if state.coding_result else [])]}
Primary Policy: {state.primary_policy.insurer_name if state.primary_policy else 'None'}
Secondary Policy: {state.secondary_policy.insurer_name if state.secondary_policy else 'None'}
Warnings: {state.warnings}
Financial Report Total Billed: {state.financial_report.breakdown.summary.total_billed if state.financial_report else 0}

Rules:
- Score 0 to 100 based on completeness, coding accuracy, policy resolution, and financial ledger consistency.
- If there are uncorrected coding inconsistencies or missing diagnoses, set passed=false and recommend RETRY_MEDICAL_CODING.
- If there are policy mismatches, set passed=false and recommend RETRY_INSURANCE.
- If quality score >= 80 and no critical flaws exist, set passed=true and action=APPROVED.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": JudgeEvaluation,
            },
        )
        parsed = json.loads(response.text)
        return JudgeEvaluation(**parsed)

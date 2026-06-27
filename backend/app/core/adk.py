import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Callable, Awaitable

from pydantic import BaseModel, Field

from app.schemas.intake import DocumentType
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.medical_coding import CodingResult
from app.schemas.insurance_engine import InsurancePolicy
from app.schemas.cob_engine import COBDecision
from app.schemas.finance_engine import FinancialReport

logger = logging.getLogger(__name__)

class FatalBusinessError(Exception):
    """Exception raised for permanent business logic failures that should never be retried."""
    pass


# Error types that represent permanent business logic failures — never retry these.
BUSINESS_ERROR_TYPES = (FatalBusinessError, RuntimeError)


class TraceEntry(BaseModel):
    """Represents a single step trace logged during multi-agent orchestration."""
    agent_name: str = Field(..., description="Name of the specialist agent executing the step")
    status: str = Field(..., description="Step execution outcome, e.g., 'success', 'retry', 'error'")
    message: str = Field(..., description="Descriptive status details or exception logging")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO timestamp of the event")


class SharedWorkflowState(BaseModel):
    """The shared mutable workflow state passed between coordinated agents."""
    claim_id: str = Field(..., description="Claim ID associated with the run")
    member_id: str = Field(..., description="Member ID of the patient")
    processed_documents: Dict[DocumentType, ProcessedDocument] = Field(default_factory=dict, description="Extracted texts from document intelligence")
    coding_result: Optional[CodingResult] = Field(None, description="Extracted clinical diagnosis and procedure codes")
    primary_policy: Optional[InsurancePolicy] = Field(None, description="Resolved primary policy details")
    secondary_policy: Optional[InsurancePolicy] = Field(None, description="Resolved secondary policy details")
    cob_decision: Optional[COBDecision] = Field(None, description="Adjudicated benefits order and coverage calculations")
    financial_report: Optional[FinancialReport] = Field(None, description="Audited payment allocations ledger")
    warnings: List[str] = Field(default_factory=list, description="Quality, low confidence, or structure audit warnings")
    trace: List[TraceEntry] = Field(default_factory=list, description="Sequence trace log details")
    errors: List[str] = Field(default_factory=list, description="Encountered execution exception details")
    workflow_status: str = Field("pending", description="Overall pipeline status: pending | running | success | failed")
    failed_agent: Optional[str] = Field(None, description="Name of the agent that caused workflow failure")
    failure_reason: Optional[str] = Field(None, description="Human-readable reason for workflow failure")


class Agent(ABC):
    """Abstract Base Class establishing the contract for all specialist agents."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, state: SharedWorkflowState) -> None:
        """Executes the specialized coordination logic and mutates the shared state."""
        pass


class Orchestrator:
    """Orchestrates agent-to-agent sequencing, workflow state handoff, error tracing, and retries."""

    def __init__(self, agents: List[Agent]):
        self.agents_list = agents
        self.agents_dict = {agent.name: agent for agent in agents}
        # Optional callback invoked after each agent completes successfully
        self._on_agent_complete: Optional[Callable[[str, int], Awaitable[None]]] = None

    def set_progress_callback(self, callback: Callable[[str, int], Awaitable[None]]) -> None:
        """Register an async callback that receives (agent_name, progress_percent) on success."""
        self._on_agent_complete = callback

    def _evaluate_next_step(self, state: SharedWorkflowState, completed_agents: set) -> tuple:
        """Dynamic planner determining which agent to run next and the reasoning why."""
        # 1. Verification of intake
        if "IntakeAgent" not in completed_agents:
            return "IntakeAgent", "Intake verification is required to validate that raw files are loaded into storage slots."

        # 2. Extracting texts (DocIntel)
        if "DocIntelAgent" not in completed_agents or not state.processed_documents:
            return "DocIntelAgent", "Raw documents are loaded. DocIntelAgent must perform OCR text extraction on the uploaded PDF/images."

        # 3. Medical Coding
        if "MedicalCodingAgent" not in completed_agents or not state.coding_result:
            return "MedicalCodingAgent", "Clinical text is extracted. MedicalCodingAgent must analyze the text to infer ICD-10 diagnoses and CPT procedure codes."

        # 4. Resolve Insurance Policies
        if "InsuranceAgent" not in completed_agents or not state.primary_policy:
            return "InsuranceAgent", "Clinical codes are ready. InsuranceAgent must load active insurance policies and map coverages matching the patient."

        # 5. COB Coordination
        if "COBAgent" not in completed_agents or not state.cob_decision:
            return "COBAgent", "Insurance policies resolved. COBAgent is selected to evaluate Coordination of Benefits rules and assign primary/secondary payer order."

        # 6. Finance Ledger Adjudication
        if "FinanceAgent" not in completed_agents or not state.financial_report:
            return "FinanceAgent", "COB decision finalized. FinanceAgent is required to compute the audited financial breakdown (deductibles, coinsurance, OOPM)."

        # 7. Quality Audit (Reviewer)
        if "ReviewerAgent" not in completed_agents:
            return "ReviewerAgent", "Financial reports generated. ReviewerAgent is chosen to perform output audits, check clinical code confidence levels, and log warning indicators."

        return None, ""

    async def execute(self, state: SharedWorkflowState, max_retries: int = 1) -> None:
        """Runs the orchestration pipeline, managing retries and tracing.

        Supports dynamic agentic planning for standard pipelines, and sequential routing
        for custom test sequences.
        """
        logger.info(f"Starting orchestration pipeline for claim {state.claim_id}")
        state.workflow_status = "running"

        # Check if this is the standard production pipeline
        is_production = len(self.agents_list) == 7 and all(
            name in self.agents_dict for name in [
                "IntakeAgent", "DocIntelAgent", "MedicalCodingAgent",
                "InsuranceAgent", "COBAgent", "FinanceAgent", "ReviewerAgent"
            ]
        )

        progress_milestones = {
            "IntakeAgent": 15,
            "DocIntelAgent": 35,
            "MedicalCodingAgent": 55,
            "InsuranceAgent": 70,
            "COBAgent": 85,
            "FinanceAgent": 95,
            "ReviewerAgent": 100,
        }

        if is_production:
            completed_agents = set()
            step_count = 0
            max_steps = 15

            while state.workflow_status == "running" and step_count < max_steps:
                step_count += 1
                next_agent_name, reasoning = self._evaluate_next_step(state, completed_agents)

                if not next_agent_name:
                    logger.info("Agentic planner completed successfully.")
                    state.workflow_status = "success"
                    break

                agent = self.agents_dict.get(next_agent_name)
                logger.info(f"Agentic Planner chose {next_agent_name}. Reason: {reasoning}")

                retry_count = 0
                success = False

                while not success:
                    try:
                        await agent.execute(state)
                        state.trace.append(
                            TraceEntry(
                                agent_name=agent.name,
                                status="success",
                                message=f"{reasoning} Status: Success."
                            )
                        )
                        completed_agents.add(agent.name)
                        success = True

                        if self._on_agent_complete:
                            progress = progress_milestones.get(agent.name, 50)
                            try:
                                await self._on_agent_complete(agent.name, progress)
                            except Exception as cb_err:
                                logger.warning(f"Progress callback error: {cb_err}")

                    except BUSINESS_ERROR_TYPES as e:
                        error_msg = str(e)
                        logger.error(f"Business error in agent {agent.name}: {error_msg}")
                        state.trace.append(
                            TraceEntry(
                                agent_name=agent.name,
                                status="error",
                                message=f"Fatal business error: {error_msg}"
                            )
                        )
                        state.errors.append(error_msg)
                        state.workflow_status = "failed"
                        state.failed_agent = agent.name
                        state.failure_reason = error_msg
                        raise RuntimeError(
                            f"Pipeline stopped: {agent.name} encountered a business error: {error_msg}"
                        ) from e

                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e)
                        logger.warning(f"Transient error in agent {agent.name} (Attempt {retry_count}): {error_msg}")

                        if retry_count <= max_retries:
                            state.trace.append(
                                TraceEntry(
                                    agent_name=agent.name,
                                    status="retry",
                                    message=f"Transient failure: {error_msg}. Retrying (attempt {retry_count})..."
                                )
                            )
                        else:
                            fatal_msg = f"Agent {agent.name} failed after {retry_count} attempts: {error_msg}"
                            state.trace.append(
                                TraceEntry(
                                    agent_name=agent.name,
                                    status="error",
                                    message=fatal_msg
                                )
                            )
                            state.errors.append(fatal_msg)
                            state.workflow_status = "failed"
                            state.failed_agent = agent.name
                            state.failure_reason = fatal_msg
                            raise RuntimeError(fatal_msg) from e

            if state.workflow_status == "running":
                state.workflow_status = "success"
        else:
            # Fallback for custom test sequences
            for agent in self.agents_list:
                retry_count = 0
                success = False

                while not success:
                    logger.info(f"Executing agent {agent.name} (Attempt {retry_count + 1})")
                    try:
                        await agent.execute(state)
                        state.trace.append(
                            TraceEntry(
                                agent_name=agent.name,
                                status="success",
                                message=f"Agent {agent.name} completed successfully."
                            )
                        )
                        success = True

                        if self._on_agent_complete:
                            progress = progress_milestones.get(agent.name, 50)
                            try:
                                await self._on_agent_complete(agent.name, progress)
                            except Exception as cb_err:
                                logger.warning(f"Progress callback error: {cb_err}")

                    except BUSINESS_ERROR_TYPES as e:
                        error_msg = str(e)
                        logger.error(f"Business error in agent {agent.name}: {error_msg}")
                        state.trace.append(
                            TraceEntry(
                                agent_name=agent.name,
                                status="error",
                                message=f"Fatal business error: {error_msg}"
                            )
                        )
                        state.errors.append(error_msg)
                        state.workflow_status = "failed"
                        state.failed_agent = agent.name
                        state.failure_reason = error_msg
                        raise RuntimeError(
                            f"Pipeline stopped: {agent.name} encountered a business error: {error_msg}"
                        ) from e

                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e)
                        logger.warning(f"Transient error in agent {agent.name} (Attempt {retry_count}): {error_msg}")

                        if retry_count <= max_retries:
                            state.trace.append(
                                TraceEntry(
                                    agent_name=agent.name,
                                    status="retry",
                                    message=f"Transient failure: {error_msg}. Retrying (attempt {retry_count})...."
                                )
                            )
                        else:
                            fatal_msg = f"Agent {agent.name} failed after {retry_count} attempts: {error_msg}"
                            state.trace.append(
                                TraceEntry(
                                    agent_name=agent.name,
                                    status="error",
                                    message=fatal_msg
                                )
                            )
                            state.errors.append(fatal_msg)
                            state.workflow_status = "failed"
                            state.failed_agent = agent.name
                            state.failure_reason = fatal_msg
                            raise RuntimeError(fatal_msg) from e

            state.workflow_status = "success"
        logger.info(f"Orchestration pipeline completed successfully for claim {state.claim_id}")
        logger.info(f"Orchestration pipeline completed successfully for claim {state.claim_id}")

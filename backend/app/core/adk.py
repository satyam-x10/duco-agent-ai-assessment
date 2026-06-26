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

# Error types that represent permanent business logic failures — never retry these.
BUSINESS_ERROR_TYPES = (ValueError, RuntimeError)


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
        self.agents = agents
        # Optional callback invoked after each agent completes successfully
        self._on_agent_complete: Optional[Callable[[str, int], Awaitable[None]]] = None

    def set_progress_callback(self, callback: Callable[[str, int], Awaitable[None]]) -> None:
        """Register an async callback that receives (agent_name, progress_percent) on success."""
        self._on_agent_complete = callback

    async def execute(self, state: SharedWorkflowState, max_retries: int = 1) -> None:
        """Runs the complete sequence of specialist agents, managing retries and tracing.

        Business errors (ValueError, RuntimeError) are treated as permanent failures — pipeline
        stops immediately with no retry. Transient I/O errors (IOError, OSError) are retried up
        to max_retries times.
        """
        logger.info(f"Starting orchestration pipeline for claim {state.claim_id}")
        state.workflow_status = "running"

        # Progress milestones per agent (percent complete after each agent finishes)
        progress_milestones = {
            "IntakeAgent": 15,
            "DocIntelAgent": 35,
            "MedicalCodingAgent": 55,
            "InsuranceAgent": 70,
            "COBAgent": 85,
            "FinanceAgent": 95,
            "ReviewerAgent": 100,
        }

        for agent in self.agents:
            retry_count = 0
            success = False

            while not success:
                logger.info(f"Executing agent {agent.name} (Attempt {retry_count + 1})")
                try:
                    await agent.execute(state)

                    # Log success trace entry
                    state.trace.append(
                        TraceEntry(
                            agent_name=agent.name,
                            status="success",
                            message=f"Agent {agent.name} completed successfully."
                        )
                    )
                    success = True

                    # Fire progress callback if registered
                    if self._on_agent_complete:
                        progress = progress_milestones.get(agent.name, 50)
                        try:
                            await self._on_agent_complete(agent.name, progress)
                        except Exception as cb_err:
                            logger.warning(f"Progress callback error: {cb_err}")

                except BUSINESS_ERROR_TYPES as e:
                    # Business/logic error — do NOT retry, stop immediately
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
                    # Potentially transient error — retry up to max_retries
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
                        # Exhausted retries
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

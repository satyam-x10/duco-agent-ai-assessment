import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.schemas.intake import DocumentType
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.medical_coding import CodingResult
from app.schemas.insurance_engine import InsurancePolicy
from app.schemas.cob_engine import COBDecision
from app.schemas.finance_engine import FinancialReport

logger = logging.getLogger(__name__)


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

    async def execute(self, state: SharedWorkflowState, max_retries: int = 3) -> None:
        """Runs the complete sequence of specialist agents, managing retries and tracing."""
        logger.info(f"Starting orchestration pipeline for claim {state.claim_id}")

        for agent in self.agents:
            retry_count = 0
            success = False

            while retry_count <= max_retries and not success:
                logger.info(f"Executing agent {agent.name} (Attempt {retry_count + 1})")
                try:
                    # Execute the specialist agent's logic
                    await agent.execute(state)
                    
                    # Log success trace entry
                    state.trace.append(
                        TraceEntry(
                            agent_name=agent.name,
                            status="success",
                            message=f"Agent {agent.name} executed successfully."
                        )
                    )
                    success = True
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Agent {agent.name} failed (Attempt {retry_count}): {e}")
                    
                    if retry_count <= max_retries:
                        # Log retry attempt trace entry
                        state.trace.append(
                            TraceEntry(
                                agent_name=agent.name,
                                status="retry",
                                message=f"Transient failure occurred: {str(e)}. Retrying..."
                            )
                        )
                    else:
                        # Log fatal failure trace entry
                        error_msg = f"Fatal error: Agent {agent.name} failed after {max_retries + 1} attempts. Error: {str(e)}"
                        state.trace.append(
                            TraceEntry(
                                agent_name=agent.name,
                                status="error",
                                message=error_msg
                            )
                        )
                        state.errors.append(error_msg)
                        # Propagate exception
                        raise RuntimeError(error_msg) from e

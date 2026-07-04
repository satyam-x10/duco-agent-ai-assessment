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

from pathlib import Path

logger = logging.getLogger(__name__)

def append_realtime_log(message: str) -> None:
    log_path = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "pipeline_realtime_trace.txt"
    timestamp = datetime.utcnow().isoformat() + "Z"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        logger.error(f"Failed to write to realtime log: {e}")

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
    ocr_engine: str = Field("gemini", description="OCR engine choice for image/scanned PDF processing: library | gemini")
    processed_documents: Dict[DocumentType, ProcessedDocument] = Field(default_factory=dict, description="Extracted texts from document intelligence")
    ocr_strategies: Dict[DocumentType, str] = Field(default_factory=dict, description="Dynamic extraction strategies resolved for document types")
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
    requires_human_approval: bool = Field(False, description="Flag indicating if the claim needs human auditor sign-off")
    human_approved: bool = Field(False, description="Whether the auditor has signed off on the claim")


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
        # Optional callback invoked just before each agent starts executing
        self._on_agent_start: Optional[Callable[[str], Awaitable[None]]] = None

    def set_progress_callback(self, callback: Callable[[str, int], Awaitable[None]]) -> None:
        """Register an async callback that receives (agent_name, progress_percent) on success."""
        self._on_agent_complete = callback

    def set_start_callback(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Register an async callback that receives (agent_name) just before an agent starts."""
        self._on_agent_start = callback

    def _evaluate_next_step(self, state: SharedWorkflowState, completed_agents: set) -> tuple:
        """Dynamic planner determining which agent to run next and the reasoning why."""
        # 1. Verification of intake
        if "IntakeAgent" not in completed_agents:
            return "IntakeAgent", "Intake verification is required to validate that raw files are loaded into storage slots."

        # 2. Extracting texts (DocIntel) - OCR confidence validation (Rule 1)
        low_confidence_doc = None
        for doc_type, doc in state.processed_documents.items():
            if doc.confidence < 0.95 and state.ocr_strategies.get(doc_type) != "high_fidelity":
                low_confidence_doc = doc_type
                break

        if low_confidence_doc:
            logger.warning(f"DocIntelAgent flagged low-confidence OCR ({state.processed_documents[low_confidence_doc].confidence}) for {low_confidence_doc.value}. Backtracking to DocIntelAgent for high-fidelity extraction strategy.")
            state.trace.append(
                TraceEntry(
                    agent_name="Orchestrator",
                    status="retry",
                    message=f"Low OCR confidence detected for {low_confidence_doc.value}. Backtracking to DocIntelAgent with high-fidelity strategy."
                )
            )
            # Remove from completed and processed documents to trigger re-run
            state.processed_documents.pop(low_confidence_doc)
            state.ocr_strategies[low_confidence_doc] = "high_fidelity"
            
            # Reset completed status for downstream agents to force re-planning
            completed_agents.discard("DocIntelAgent")
            completed_agents.discard("MedicalCodingAgent")
            completed_agents.discard("InsuranceAgent")
            completed_agents.discard("COBAgent")
            completed_agents.discard("FinanceAgent")
            completed_agents.discard("ReviewerAgent")
            return "DocIntelAgent", f"Retrying OCR text extraction with high-fidelity strategy on {low_confidence_doc.value}."

        if "DocIntelAgent" not in completed_agents or not state.processed_documents:
            return "DocIntelAgent", "Raw documents are loaded. DocIntelAgent must perform OCR text extraction on the uploaded PDF/images."

        # 3. Medical Coding - Empty diagnosis handling (Rule 2)
        if "MedicalCodingAgent" in completed_agents and state.coding_result:
            if not state.coding_result.diagnoses:
                coding_runs = sum(1 for entry in state.trace if entry.agent_name == "MedicalCodingAgent")
                if coding_runs < 2:
                    logger.warning("No diagnoses extracted by MedicalCodingAgent. Retrying Medical Coding...")
                    state.trace.append(
                        TraceEntry(
                            agent_name="Orchestrator",
                            status="retry",
                            message="No diagnoses extracted from clinical documents. Backtracking to MedicalCodingAgent for self-correction."
                        )
                    )
                    state.coding_result = None
                    completed_agents.discard("MedicalCodingAgent")
                    completed_agents.discard("InsuranceAgent")
                    completed_agents.discard("COBAgent")
                    completed_agents.discard("FinanceAgent")
                    completed_agents.discard("ReviewerAgent")
                    return "MedicalCodingAgent", "No diagnoses were extracted. Retrying medical coding with reflection."
                else:
                    # Already retried once. Skip remaining agents and request human clarification
                    logger.info("No diagnoses extracted after retry. Halting pipeline to request clinician clarification.")
                    state.requires_human_approval = True
                    return None, "No diagnoses extracted. Halting pipeline for manual clinician clarification."

        if "MedicalCodingAgent" not in completed_agents or not state.coding_result:
            return "MedicalCodingAgent", "Clinical text is extracted. MedicalCodingAgent must analyze the text to infer ICD-10 diagnoses and CPT procedure codes."

        # 4. Resolve Insurance Policies
        if "InsuranceAgent" not in completed_agents or not state.primary_policy:
            return "InsuranceAgent", "Clinical codes are ready. InsuranceAgent must load active insurance policies and map coverages matching the patient."

        # 5. COB Coordination - Bypass if single policy exists (Rule 3)
        if "COBAgent" not in completed_agents or not state.cob_decision:
            if state.primary_policy and not state.secondary_policy:
                # Bypass COBAgent! Calculate COB decision directly.
                logger.info("Only one active insurance policy exists. Bypassing COBAgent.")
                state.trace.append(
                    TraceEntry(
                        agent_name="Orchestrator",
                        status="success",
                        message="Single active policy resolved. Bypassing COBAgent execution step."
                    )
                )
                cob_agent = self.agents_dict.get("COBAgent")
                if cob_agent:
                    from app.schemas.cob_engine import Claim, ClaimLine
                    from agents.cob import CPT_BILLED_AMOUNTS
                    claim_lines = []
                    for procedure in state.coding_result.procedures:
                        billed_amount = CPT_BILLED_AMOUNTS.get(procedure.code, 500.00)
                        claim_lines.append(ClaimLine(cpt_code=procedure.code, billed_amount=billed_amount))
                    claim = Claim(
                        claim_id=f"CLAIM-{state.claim_id}",
                        member_id=state.member_id,
                        lines=claim_lines
                    )
                    state.cob_decision = cob_agent.cob_engine.coordinate_benefits(claim)
                completed_agents.add("COBAgent")
            else:
                return "COBAgent", "Insurance policies resolved. COBAgent is selected to evaluate Coordination of Benefits rules and assign primary/secondary payer order."

        # 6. Finance Ledger Adjudication
        if "FinanceAgent" not in completed_agents or not state.financial_report:
            return "FinanceAgent", "COB decision finalized. FinanceAgent is required to compute the audited financial breakdown (deductibles, coinsurance, OOPM)."

        # 7. Quality Audit (Reviewer)
        if "ReviewerAgent" not in completed_agents:
            return "ReviewerAgent", "Financial reports generated. ReviewerAgent is chosen to perform output audits, check clinical code confidence levels, and log warning indicators."

        # 8. Reviewer Inconsistency Backtracking (Rule 5)
        if "ReviewerAgent" in completed_agents:
            has_coding_inconsistency = any("[Coding Inconsistency]" in w or "Low confidence" in w for w in state.warnings)
            has_policy_inconsistency = any("[Policy Inconsistency]" in w for w in state.warnings)

            if has_coding_inconsistency:
                coding_runs = sum(1 for entry in state.trace if entry.agent_name == "MedicalCodingAgent")
                if coding_runs < 2:
                    logger.warning("ReviewerAgent flagged coding/clinical inconsistency. Initiating backtracking loop to MedicalCodingAgent.")
                    state.trace.append(
                        TraceEntry(
                            agent_name="Orchestrator",
                            status="retry",
                            message="Reviewer flagged coding inconsistency. Backtracking to MedicalCodingAgent for self-correction."
                        )
                    )
                    completed_agents.discard("MedicalCodingAgent")
                    completed_agents.discard("InsuranceAgent")
                    completed_agents.discard("COBAgent")
                    completed_agents.discard("FinanceAgent")
                    completed_agents.discard("ReviewerAgent")
                    # Retain inconsistency warning for reflection prompt
                    state.warnings = [w for w in state.warnings if "[Coding Inconsistency]" in w or "Low confidence" in w]
                    state.requires_human_approval = False
                    return "MedicalCodingAgent", "Reviewer flagged coding inconsistency. Backtracking to MedicalCodingAgent for correction."

            if has_policy_inconsistency:
                insurance_runs = sum(1 for entry in state.trace if entry.agent_name == "InsuranceAgent")
                if insurance_runs < 2:
                    logger.warning("ReviewerAgent flagged policy mismatch/inconsistency. Initiating backtracking loop to InsuranceAgent.")
                    state.trace.append(
                        TraceEntry(
                            agent_name="Orchestrator",
                            status="retry",
                            message="Reviewer flagged policy inconsistency. Backtracking to InsuranceAgent for correction."
                        )
                    )
                    completed_agents.discard("InsuranceAgent")
                    completed_agents.discard("COBAgent")
                    completed_agents.discard("FinanceAgent")
                    completed_agents.discard("ReviewerAgent")
                    # Retain policy warning
                    state.warnings = [w for w in state.warnings if "[Policy Inconsistency]" in w]
                    state.requires_human_approval = False
                    return "InsuranceAgent", "Reviewer flagged policy inconsistency. Backtracking to InsuranceAgent for correction."

        return None, ""

    async def execute(self, state: SharedWorkflowState, max_retries: int = 1) -> None:
        """Runs the orchestration pipeline, managing retries and tracing.

        Supports dynamic agentic planning for standard pipelines, and sequential routing
        for custom test sequences.
        """
        logger.info(f"Starting orchestration pipeline for claim {state.claim_id}")
        append_realtime_log(f"--- STARTING ORCHESTRATION PIPELINE for Claim: {state.claim_id} Patient Member: {state.member_id} ---")
        append_realtime_log(f"Selected OCR Engine: {state.ocr_engine}")
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
                
                num_traces_before = len(state.trace)
                next_agent_name, reasoning = self._evaluate_next_step(state, completed_agents)

                if len(state.trace) > num_traces_before:
                    for i in range(num_traces_before, len(state.trace)):
                        entry = state.trace[i]
                        if entry.status == "retry":
                            append_realtime_log(f"[Backtracking Detected] {entry.message}")

                if not next_agent_name:
                    logger.info("Agentic planner completed successfully.")
                    state.workflow_status = "success"
                    break

                agent = self.agents_dict.get(next_agent_name)
                logger.info(f"Agentic Planner chose {next_agent_name}. Reason: {reasoning}")
                append_realtime_log(f"[Planner Choice] Chose {next_agent_name}. Reason: {reasoning}")

                retry_count = 0
                success = False

                while not success:
                    try:
                        append_realtime_log(f"[Agent Start] Executing {agent.name} (Attempt {retry_count + 1})...")
                        # Fire start callback so frontend knows which agent is actively running
                        if self._on_agent_start:
                            try:
                                await self._on_agent_start(agent.name)
                            except Exception as cb_err:
                                logger.warning(f"Start callback error: {cb_err}")
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

                        # Real-time state logging after success!
                        append_realtime_log(f"[Agent Success] Completed {agent.name} successfully.")
                        if agent.name == "DocIntelAgent":
                            for doc_type, doc in state.processed_documents.items():
                                parser = doc.metadata.get("parser", "Unknown")
                                engine = doc.metadata.get("ocr_engine", "gemini")
                                path = doc.metadata.get("file_path", "unknown_path")
                                append_realtime_log(
                                    f"  -> Extracted text from {doc_type.value} using parser '{parser}' (Engine: '{engine}') with confidence {doc.confidence} from '{Path(path).name}':"
                                )
                                # Log the actual extracted text
                                append_realtime_log(f"===== EXTRACTED TEXT FROM {doc_type.value} =====\n{doc.extracted_text}\n==================================================")
                        elif agent.name == "MedicalCodingAgent" and state.coding_result:
                            diags = [f"{d.code} ({d.description}, confidence: {d.confidence})" for d in state.coding_result.diagnoses]
                            procs = [f"{p.code} ({p.description}, confidence: {p.confidence})" for p in state.coding_result.procedures]
                            append_realtime_log(f"  -> Extracted Diagnoses: {', '.join(diags) if diags else 'None'}")
                            append_realtime_log(f"  -> Extracted Procedures: {', '.join(procs) if procs else 'None'}")
                        elif agent.name == "InsuranceAgent":
                            pri = f"{state.primary_policy.provider_name} ({state.primary_policy.policy_id})" if state.primary_policy else "None"
                            sec = f"{state.secondary_policy.provider_name} ({state.secondary_policy.policy_id})" if state.secondary_policy else "None"
                            append_realtime_log(f"  -> Resolved primary coverage: {pri}")
                            append_realtime_log(f"  -> Resolved secondary coverage: {sec}")
                        elif agent.name == "COBAgent" and state.cob_decision:
                            append_realtime_log(f"  -> Payment Order Resolved: Primary Plan={state.cob_decision.primary_policy_id}, Secondary Plan={state.cob_decision.secondary_policy_id or 'None'}")
                        elif agent.name == "FinanceAgent" and state.financial_report:
                            summary = state.financial_report.breakdown.summary
                            resp = state.financial_report.breakdown.patient_responsibility
                            append_realtime_log(
                                f"  -> Coordinated Benefits Ledger: Billed ₹{summary.total_billed:.2f}, Primary Paid ₹{summary.total_primary_paid:.2f}, Secondary Paid ₹{summary.total_secondary_paid:.2f}, Coordinated Patient Responsibility ₹{summary.total_patient_responsibility:.2f}"
                            )
                            append_realtime_log(
                                f"  -> Out-of-pocket splits: Deductible satisfied ₹{resp.total_deductible:.2f}, Coinsurance applied ₹{resp.total_coinsurance:.2f}"
                            )
                            # Log actual coordinated explanation notes
                            append_realtime_log(f"===== FINANCIAL EXPLANATION NOTES =====\n{resp.explanation_notes}\n========================================")
                        elif agent.name == "ReviewerAgent":
                            append_realtime_log(f"  -> Warnings: {state.warnings}")
                            append_realtime_log(f"  -> Requires manual clinician approval: {state.requires_human_approval}")

                        if self._on_agent_complete:
                            progress = progress_milestones.get(agent.name, 50)
                            try:
                                await self._on_agent_complete(agent.name, progress)
                            except Exception as cb_err:
                                logger.warning(f"Progress callback error: {cb_err}")

                    except BUSINESS_ERROR_TYPES as e:
                        error_msg = str(e)
                        logger.error(f"Business error in agent {agent.name}: {error_msg}")
                        append_realtime_log(f"[Agent Fatal Error] {agent.name} encountered a business error: {error_msg}")
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
                        append_realtime_log(f"--- ORCHESTRATION PIPELINE COMPLETED (Status: {state.workflow_status}) ---")
                        raise RuntimeError(
                            f"Pipeline stopped: {agent.name} encountered a business error: {error_msg}"
                        ) from e

                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e)
                        logger.warning(f"Transient error in agent {agent.name} (Attempt {retry_count}): {error_msg}")
                        append_realtime_log(f"[Agent Transient Error] {agent.name} (Attempt {retry_count}): {error_msg}")

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
                            append_realtime_log(f"--- ORCHESTRATION PIPELINE COMPLETED (Status: {state.workflow_status}) ---")
                            raise RuntimeError(fatal_msg) from e

            if state.workflow_status == "running":
                state.workflow_status = "success"
            append_realtime_log(f"--- ORCHESTRATION PIPELINE COMPLETED (Status: {state.workflow_status}) ---")
        else:
            # Fallback for custom test sequences
            for agent in self.agents_list:
                retry_count = 0
                success = False

                while not success:
                    logger.info(f"Executing agent {agent.name} (Attempt {retry_count + 1})")
                    try:
                        # Fire start callback
                        if self._on_agent_start:
                            try:
                                await self._on_agent_start(agent.name)
                            except Exception as cb_err:
                                logger.warning(f"Start callback error: {cb_err}")
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

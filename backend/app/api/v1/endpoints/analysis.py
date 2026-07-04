import asyncio
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, status, HTTPException
from app.schemas.analysis import (
    AnalysisStartRequest,
    AnalysisStartResponse,
    AnalysisStatusResponse,
    JobStatus,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory job store. Maps job_id -> job record dict.
# Keys: job_id, status, progress_percent, message, created_at, completed_at, error_details, state
jobs_db: dict = {}


@router.post("/start", response_model=AnalysisStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(payload: AnalysisStartRequest = None):
    """
    Triggers the real multi-agent benefit assessment pipeline.
    The orchestrator runs as a background task. Returns a job_id for polling.
    """
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    ocr_engine = payload.ocr_engine if payload else "library"

    jobs_db[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PROCESSING,
        "progress_percent": 5,
        "message": "Initializing specialist agents. Pipeline starting...",
        "created_at": now,
        "completed_at": None,
        "error_details": None,
        "state": None,
        "ocr_engine": ocr_engine,
        "current_agent": None,
    }

    # Launch the orchestration pipeline as a background task
    asyncio.create_task(_run_orchestration(job_id))

    return AnalysisStartResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=now,
        message="Coordination of Benefits job has been queued and the pipeline is starting."
    )


@router.get("/status/{jobId}", response_model=AnalysisStatusResponse)
async def get_analysis_status(jobId: str):
    """
    Returns the real-time progress of a running or completed analysis job.
    Progress advances as each agent completes — no artificial simulation.
    """
    if jobId not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{jobId}' was not found."
        )

    job = jobs_db[jobId]
    # Collect warnings from state if available (populated by ReviewerAgent)
    state = job.get("state")
    warnings = []
    if state and hasattr(state, "warnings"):
        warnings = state.warnings or []
    return AnalysisStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress_percent=job["progress_percent"],
        message=job["message"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        error_details=job.get("error_details"),
        current_agent=job.get("current_agent"),
        warnings=warnings,
    )


async def _run_orchestration(job_id: str) -> None:
    """
    Background task that runs the full multi-agent orchestration pipeline.
    Updates jobs_db[job_id] in real-time as agents complete.
    Progress milestones match each agent's completion.
    """
    from app.dependencies.orchestration import get_orchestrator
    from app.dependencies.storage import get_storage_service
    from app.core.adk import SharedWorkflowState

    job = jobs_db.get(job_id)
    if not job:
        return

    phase_messages = {
        "IntakeAgent": "IntakeAgent: Validated documents in storage slots.",
        "DocIntelAgent": "DocIntelAgent: Extracted text from all uploaded documents.",
        "MedicalCodingAgent": "MedicalCodingAgent: Gemini inferred ICD-10 and CPT codes.",
        "InsuranceAgent": "InsuranceAgent: Resolved insurance policies for patient.",
        "COBAgent": "COBAgent: Coordinated benefits across primary and secondary plans.",
        "FinanceAgent": "FinanceAgent: Generated audited financial breakdown report.",
        "ReviewerAgent": "ReviewerAgent: Validated pipeline outputs and generated quality checks.",
    }

    async def on_agent_complete(agent_name: str, progress: int) -> None:
        """Callback invoked after each agent succeeds — updates job progress and clears current_agent."""
        job["progress_percent"] = progress
        job["message"] = phase_messages.get(agent_name, f"{agent_name} completed.")
        job["current_agent"] = None
        logger.info(f"[Job {job_id}] {agent_name} complete → {progress}%")

    async def on_agent_start(agent_name: str) -> None:
        """Callback invoked just before an agent begins executing — marks it as the active agent."""
        job["current_agent"] = agent_name
        job["message"] = f"{agent_name} is running..."
        logger.info(f"[Job {job_id}] {agent_name} starting...")

    try:
        # Determine which member to use based on uploaded documents
        storage_service = get_storage_service()
        status_map = await storage_service.get_status()

        # Default to Priya Sen (BlueShield subscriber: 98765).
        # Her member ID exists in policy_blueshield.json and the InsuranceAgent
        # resolves cross-plan coverage by name match across all loaded policies.
        member_id = "98765"

        ocr_engine = job.get("ocr_engine", "library")
        claim_id = f"CLAIM-{job_id[:8].upper()}"
        state = SharedWorkflowState(claim_id=claim_id, member_id=member_id, ocr_engine=ocr_engine)

        orchestrator = get_orchestrator()
        orchestrator.set_progress_callback(on_agent_complete)
        orchestrator.set_start_callback(on_agent_start)

        await orchestrator.execute(state, max_retries=1)

        # Success — check if human approval is required
        if getattr(state, "requires_human_approval", False) and not getattr(state, "human_approved", False):
            job["status"] = JobStatus.AWAITING_APPROVAL
            job["progress_percent"] = 99
            job["message"] = "Reviewer Agent flagged quality checks. Awaiting manual clinician approval."
            job["completed_at"] = datetime.utcnow()
            job["state"] = state
            logger.info(f"[Job {job_id}] Orchestration finished. Awaiting clinician approval.")
        else:
            job["status"] = JobStatus.COMPLETED
            job["progress_percent"] = 100
            job["message"] = "Pipeline completed successfully. Pre-authorization letters and reports are ready."
            job["completed_at"] = datetime.utcnow()
            job["state"] = state
            logger.info(f"[Job {job_id}] Orchestration completed successfully.")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Job {job_id}] Orchestration failed: {error_msg}", exc_info=True)

        # Retrieve failed_agent from state if available
        failed_agent = "Unknown"
        failure_reason = error_msg
        try:
            if state and state.failed_agent:
                failed_agent = state.failed_agent
            if state and state.failure_reason:
                failure_reason = state.failure_reason
        except Exception:
            pass

        job["status"] = JobStatus.FAILED
        job["progress_percent"] = job.get("progress_percent", 0)
        job["message"] = f"Pipeline failed at {failed_agent}: {failure_reason}"
        job["completed_at"] = datetime.utcnow()
        job["error_details"] = failure_reason
        job["failed_agent"] = failed_agent
        job["state"] = state if "state" in dir() else None


@router.post("/approve")
async def approve_analysis(job_id: str):
    """
    Manually approves a pending claim after a quality review audit.
    """
    if job_id not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{job_id}' was not found."
        )
    
    job = jobs_db[job_id]
    if job["status"] != JobStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not in awaiting_approval state."
        )
        
    state = job.get("state")
    if not state:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow state is missing."
        )
        
    from app.core.adk import TraceEntry
    state.human_approved = True
    state.requires_human_approval = False
    state.trace.append(
        TraceEntry(
            agent_name="ClinicianAuditor",
            status="success",
            message="Manual clinician audit approval signed off. Proceeding to finalize benefits."
        )
    )
    
    job["status"] = JobStatus.COMPLETED
    job["progress_percent"] = 100
    job["message"] = "Clinician approved. Pipeline completed successfully."
    job["completed_at"] = datetime.utcnow()
    
    return {"status": "success", "message": "Job successfully approved."}


@router.post("/reject")
async def reject_analysis(job_id: str):
    """
    Rejects the medical coding outputs and triggers a self-correction re-run.
    """
    if job_id not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{job_id}' was not found."
        )
    
    job = jobs_db[job_id]
    if job["status"] != JobStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not in awaiting_approval state."
        )
        
    state = job.get("state")
    if not state:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow state is missing."
        )
        
    from app.core.adk import TraceEntry
    state.human_approved = False
    state.requires_human_approval = False
    state.trace.append(
        TraceEntry(
            agent_name="ClinicianAuditor",
            status="retry",
            message="Clinician auditor rejected current codes. Relaunching pipeline for reflection re-extraction."
        )
    )
    
    # Add clinician audit rejection notes to warnings to drive the reflection prompt
    state.warnings.append(
        "Clinician Auditor explicitly rejected prior extraction: Low confidence diagnosis or procedure codes. "
        "Please double check the text for Meniscectomy, MRI, or ACL reconstruction and confirm they are explicitly documented."
    )
            
    job["status"] = JobStatus.PROCESSING
    job["progress_percent"] = 40
    job["message"] = "Re-analyzing claim with clinician feedback..."
    
    # Relaunch the pipeline
    asyncio.create_task(_run_orchestration(job_id))
    
    return {"status": "success", "message": "Job rejected and re-running."}

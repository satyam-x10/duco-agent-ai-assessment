import asyncio
import json
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, status, HTTPException
from fastapi.responses import StreamingResponse
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

# Active SSE subscriber queues per job_id
job_event_subscribers: Dict[str, List[asyncio.Queue]] = {}


async def broadcast_job_event(job_id: str, event_type: str, data: dict) -> None:
    """Broadcasts a structured event to all active SSE subscribers for a job."""
    if job_id not in job_event_subscribers:
        return
    payload = {
        "job_id": job_id,
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **data,
    }
    dead_queues = []
    for queue in job_event_subscribers[job_id]:
        try:
            await queue.put(payload)
        except Exception:
            dead_queues.append(queue)
    for q in dead_queues:
        job_event_subscribers[job_id].remove(q)


@router.get("/stream/{jobId}")
async def stream_analysis_events(jobId: str):
    """
    Server-Sent Events (SSE) stream providing real-time agent execution events,
    tool invocations, and live parsed log lines as they are produced.
    """
    if jobId not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{jobId}' was not found."
        )

    async def event_generator():
        queue = asyncio.Queue()
        if jobId not in job_event_subscribers:
            job_event_subscribers[jobId] = []
        job_event_subscribers[jobId].append(queue)

        try:
            # Emit current snapshot
            current_job = jobs_db[jobId]
            initial_payload = {
                "event": "initial_snapshot",
                "status": current_job["status"],
                "progress_percent": current_job["progress_percent"],
                "message": current_job["message"],
                "current_agent": current_job.get("current_agent"),
            }
            yield f"data: {json.dumps(initial_payload)}\n\n"

            # If already terminated, return immediately
            if current_job["status"] in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.AWAITING_APPROVAL):
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=12.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("event") in ("completed", "failed", "awaiting_approval"):
                        break
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield ": ping\n\n"
        finally:
            if jobId in job_event_subscribers and queue in job_event_subscribers[jobId]:
                job_event_subscribers[jobId].remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/start", response_model=AnalysisStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(payload: AnalysisStartRequest = None):
    """
    Triggers the real multi-agent benefit assessment pipeline.
    The orchestrator runs as a background task. Returns a job_id for polling or SSE streaming.
    """
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    ocr_engine = payload.ocr_engine if payload else "library"
    mock_mode = payload.mock_mode if payload else False

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
        "mock_mode": mock_mode,
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


def _finalize_artifacts(state) -> None:
    """Build deterministic final artifacts only after required approval."""
    from app.dependencies.audio import get_audio_briefing_service

    state.audio_briefing = get_audio_briefing_service().generate_briefing(state).briefing
    state.artifacts_finalized = True



async def _run_orchestration(job_id: str, existing_state=None) -> None:
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

    if existing_state is None:
        # Clear the realtime trace log only for a new run, not a clinician
        # correction pass whose earlier evidence must remain auditable.
        from app.core.adk import clear_realtime_log
        clear_realtime_log()

    phase_messages = {
        "IntakeAgent": "IntakeAgent: Validated documents in storage slots.",
        "DocIntelAgent": "DocIntelAgent: Extracted text from all uploaded documents.",
        "MedicalCodingAgent": "MedicalCodingAgent: Extracted or inferred ICD-10 and CPT codes with evidence.",
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
        await broadcast_job_event(job_id, "agent_complete", {
            "agent_name": agent_name,
            "progress_percent": progress,
            "message": job["message"],
            "status": job["status"],
        })

    async def on_agent_start(agent_name: str) -> None:
        """Callback invoked just before an agent begins executing — marks it as the active agent."""
        job["current_agent"] = agent_name
        job["message"] = f"{agent_name} is running..."
        
        # Start milestones to update progress bar dynamically when starting each agent
        start_milestones = {
            "IntakeAgent": 10,
            "DocIntelAgent": 25,
            "MedicalCodingAgent": 45,
            "InsuranceAgent": 62,
            "COBAgent": 78,
            "FinanceAgent": 90,
            "ReviewerAgent": 98,
        }
        if agent_name in start_milestones:
            job["progress_percent"] = start_milestones[agent_name]
            
        logger.info(f"[Job {job_id}] {agent_name} starting...")
        await broadcast_job_event(job_id, "agent_start", {
            "agent_name": agent_name,
            "progress_percent": job["progress_percent"],
            "message": job["message"],
            "status": job["status"],
        })

    async def on_agent_log(log_line: str) -> None:
        """Callback invoked when realtime logs or trace thoughts are generated."""
        await broadcast_job_event(job_id, "agent_log", {
            "log": log_line,
            "current_agent": job.get("current_agent"),
        })

    try:
        # Patient identities are resolved from structured document facts by the
        # InsuranceAgent. This sentinel is never used for adjudication.
        member_id = "UNRESOLVED"

        ocr_engine = job.get("ocr_engine", "library")
        mock_mode = job.get("mock_mode", False)
        claim_id = f"CLAIM-{job_id[:8].upper()}"
        state = existing_state or SharedWorkflowState(
            claim_id=claim_id,
            member_id=member_id,
            ocr_engine=ocr_engine,
            mock_mode=mock_mode,
        )
        state.artifacts_finalized = False

        orchestrator = get_orchestrator()
        orchestrator.set_progress_callback(on_agent_complete)
        orchestrator.set_start_callback(on_agent_start)
        orchestrator.set_log_callback(on_agent_log)

        await orchestrator.execute(state, max_retries=1)

        # Success — check if human approval is required
        if getattr(state, "requires_human_approval", False) and not getattr(state, "human_approved", False):
            job["status"] = JobStatus.AWAITING_APPROVAL
            job["progress_percent"] = 99
            job["message"] = "Reviewer Agent flagged quality checks. Awaiting manual clinician approval."
            job["completed_at"] = datetime.utcnow()
            job["state"] = state
            logger.info(f"[Job {job_id}] Orchestration finished. Awaiting clinician approval.")
            await broadcast_job_event(job_id, "awaiting_approval", {
                "progress_percent": 99,
                "message": job["message"],
                "warnings": state.warnings,
                "status": JobStatus.AWAITING_APPROVAL,
            })
        else:
            _finalize_artifacts(state)
            job["status"] = JobStatus.COMPLETED
            job["progress_percent"] = 100
            job["message"] = "Pipeline completed successfully. Pre-authorization letters and reports are ready."
            job["completed_at"] = datetime.utcnow()
            job["state"] = state
            logger.info(f"[Job {job_id}] Orchestration completed successfully.")
            await broadcast_job_event(job_id, "completed", {
                "progress_percent": 100,
                "message": job["message"],
                "status": JobStatus.COMPLETED,
            })

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
        await broadcast_job_event(job_id, "failed", {
            "progress_percent": job["progress_percent"],
            "message": job["message"],
            "error_details": failure_reason,
            "failed_agent": failed_agent,
            "status": JobStatus.FAILED,
        })


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
    _finalize_artifacts(state)
    
    job["status"] = JobStatus.COMPLETED
    job["progress_percent"] = 100
    job["message"] = "Clinician approved. Pipeline completed successfully."
    job["completed_at"] = datetime.utcnow()
    
    return {"status": "success", "message": "Job successfully approved."}


@router.post("/reject")
async def reject_analysis(job_id: str, feedback: Optional[str] = None):
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
    state.artifacts_finalized = False
    state.trace.append(
        TraceEntry(
            agent_name="ClinicianAuditor",
            status="retry",
            message="Clinician auditor rejected current codes. Relaunching pipeline for reflection re-extraction."
        )
    )
    
    # Add clinician audit rejection notes to warnings to drive the reflection prompt
    correction = feedback or "Re-check every diagnosis and procedure against the uploaded source evidence."
    state.warnings.append(
        f"Clinician Auditor rejected the prior extraction (Low confidence correction request): {correction}"
    )
            
    job["status"] = JobStatus.PROCESSING
    job["progress_percent"] = 40
    job["message"] = "Re-analyzing claim with clinician feedback..."
    
    # Relaunch the pipeline
    asyncio.create_task(_run_orchestration(job_id, existing_state=state))
    
    return {"status": "success", "message": "Job rejected and re-running."}


@router.get("/history", response_model=List[AnalysisStatusResponse])
async def get_analysis_history():
    """
    Returns the list of all analysis jobs, sorted by creation time (newest first).
    """
    sorted_jobs = sorted(
        jobs_db.values(),
        key=lambda j: j["created_at"],
        reverse=True
    )
    
    history = []
    for job in sorted_jobs:
        state = job.get("state")
        warnings = []
        if state and hasattr(state, "warnings"):
            warnings = state.warnings or []
        history.append(
            AnalysisStatusResponse(
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
        )
    return history


@router.post("/clear-history")
async def clear_analysis_history():
    """
    Clears all job runs from the in-memory history.
    """
    jobs_db.clear()
    return {"status": "success", "message": "Job history cleared successfully."}


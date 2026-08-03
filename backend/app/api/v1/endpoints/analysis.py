import asyncio
import uuid
import logging
from datetime import datetime
from typing import List
import json
from fastapi import APIRouter, status, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse
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

    # Clear the realtime trace log at the start of a new run
    from app.core.adk import clear_realtime_log
    clear_realtime_log()

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

    try:
        # Determine which member to use based on uploaded documents
        storage_service = get_storage_service()
        status_map = await storage_service.get_status()

        # Default to Priya Sen (BlueShield subscriber: 98765).
        # Her member ID exists in policy_blueshield.json and the InsuranceAgent
        # resolves cross-plan coverage by name match across all loaded policies.
        member_id = "98765"

        ocr_engine = job.get("ocr_engine", "library")
        mock_mode = job.get("mock_mode", False)
        claim_id = f"CLAIM-{job_id[:8].upper()}"
        state = SharedWorkflowState(claim_id=claim_id, member_id=member_id, ocr_engine=ocr_engine, mock_mode=mock_mode)

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


@router.get("/stream/{job_id}")
async def stream_agent_logs(job_id: str):
    """
    Streams parsed real-time agent execution logs and trace events via Server-Sent Events (SSE).
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    async def log_event_generator():
        sent_indices = 0
        while True:
            job = jobs_db.get(job_id)
            if not job:
                break
            state = job.get("state")
            if state and hasattr(state, "trace"):
                traces = state.trace
                if sent_indices < len(traces):
                    for entry in traces[sent_indices:]:
                        payload = json.dumps({
                            "agent_name": entry.agent_name,
                            "status": entry.status,
                            "message": entry.message,
                            "timestamp": entry.timestamp,
                            "current_agent": job.get("current_agent"),
                            "progress": job.get("progress_percent", 0),
                            "judge_evaluation": getattr(state, "judge_evaluation", None),
                        })
                        yield f"data: {payload}\n\n"
                    sent_indices = len(traces)
            
            if job.get("status") in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.AWAITING_APPROVAL] and sent_indices >= len(getattr(state, "trace", [])):
                done_payload = json.dumps({"status": job.get("status"), "message": "STREAM_FINISHED"})
                yield f"data: {done_payload}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(log_event_generator(), media_type="text/event-stream")


@router.get("/{job_id}/audio")
async def get_verdict_audio(job_id: str):
    """
    Generates and returns the Text-to-Speech (TTS) audio narration summary briefing for the claim verdict.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    job = jobs_db[job_id]
    state = job.get("state")
    if not state:
        raise HTTPException(status_code=400, detail="Job state is not ready.")

    from services.audio import AudioBriefingService
    audio_service = AudioBriefingService()
    audio_response = audio_service.generate_briefing(state)

    return {
        "job_id": job_id,
        "claim_id": state.claim_id,
        "briefing": audio_response.briefing.model_dump(),
        "generated_at": audio_response.generated_at
    }


@router.get("/{job_id}/hitl-status")
async def get_hitl_status(job_id: str):
    """
    Retrieves human-in-the-loop (HITL) audit state and details of items requiring clinician review.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    job = jobs_db[job_id]
    state = job.get("state")
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "requires_human_approval": getattr(state, "requires_human_approval", False) if state else False,
        "human_approved": getattr(state, "human_approved", False) if state else False,
        "judge_evaluation": getattr(state, "judge_evaluation", None) if state else None,
        "warnings": getattr(state, "warnings", []) if state else [],
        "coding_result": state.coding_result.model_dump() if state and state.coding_result else None,
    }


@router.post("/{job_id}/override")
async def override_and_resume(job_id: str, payload: dict = Body(...)):
    """
    Allows a human auditor to override ICD-10 or CPT codes or member details and resume pipeline execution.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    job = jobs_db[job_id]
    state = job.get("state")
    if not state:
        raise HTTPException(status_code=400, detail="State not initialized.")

    from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
    from app.core.adk import TraceEntry

    new_diagnoses = payload.get("diagnoses")
    new_procedures = payload.get("procedures")

    if new_diagnoses is not None:
        state.coding_result = state.coding_result or CodingResult()
        state.coding_result.diagnoses = [Diagnosis(code=d["code"], description=d.get("description", ""), confidence=1.0) for d in new_diagnoses]

    if new_procedures is not None:
        state.coding_result = state.coding_result or CodingResult()
        state.coding_result.procedures = [Procedure(code=p["code"], description=p.get("description", ""), confidence=1.0) for p in new_procedures]

    state.human_approved = True
    state.requires_human_approval = False
    state.trace.append(
        TraceEntry(
            agent_name="ClinicianAuditor",
            status="success",
            message="Human Auditor supplied manual code override. Resuming pipeline execution."
        )
    )

    job["status"] = JobStatus.PROCESSING
    job["message"] = "Overridden code state accepted. Resuming adjudication pipeline..."
    asyncio.create_task(_run_orchestration(job_id))

    return {"status": "success", "message": "Override applied and job resumed."}


@router.post("/documents/generate-scanned")
async def generate_synthetic_scanned_document(payload: dict = Body(...)):
    """
    Generates a realistic synthetic scanned medical document with rotation and noise artifacts for intake testing.
    """
    from services.document_generator import doc_generator
    title = payload.get("title", "SUMMIT HEALTHCARE CLINIC")
    doc_cat = payload.get("document_category", "Surgeon Cost Estimate")
    patient_name = payload.get("patient_name", "Priya Sen")
    member_id = payload.get("member_id", "MEM-882194")
    cpt_code = payload.get("cpt_code", "29881")
    cpt_desc = payload.get("cpt_desc", "Knee Arthroscopy with Meniscectomy")
    estimated_amount = float(payload.get("estimated_amount", 3200.00))

    generated_path = doc_generator.generate_scanned_image(
        title=title,
        document_category=doc_cat,
        patient_name=patient_name,
        member_id=member_id,
        cpt_code=cpt_code,
        cpt_desc=cpt_desc,
        estimated_amount=estimated_amount
    )

    return {
        "status": "success",
        "filename": generated_path.name,
        "file_path": str(generated_path),
        "message": f"Synthetic scanned document '{generated_path.name}' generated successfully."
    }



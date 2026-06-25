import uuid
from datetime import datetime
from fastapi import APIRouter, status, HTTPException
from app.schemas.analysis import (
    AnalysisStartRequest,
    AnalysisStartResponse,
    AnalysisStatusResponse,
    JobStatus,
)

router = APIRouter()

# In-memory database holding analysis jobs status
mock_jobs_db = {}


@router.post("/start", response_model=AnalysisStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(payload: AnalysisStartRequest = None):
    """
    Triggers the multi-agent benefit assessment and COB rules calculations.
    Returns a Job ID to query progress in the background.
    """
    job_id = str(uuid.uuid4())
    mock_jobs_db[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PROCESSING,
        "progress_percent": 15,
        "message": "Intake Agent validation completed. Initializing specialist agents...",
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "error_details": None,
    }
    
    return AnalysisStartResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=datetime.utcnow(),
        message="Coordination of Benefits job has been queued successfully."
    )


@router.get("/status/{jobId}", response_model=AnalysisStatusResponse)
async def get_analysis_status(jobId: str):
    """
    Queries progress status of an active benefit assessment run.
    Simulates incremental task advances on consecutive status polls.
    """
    if jobId not in mock_jobs_db:
        # Check if they passed a static placeholder (for mock frontend tests)
        if jobId == "mock-job-id":
            return AnalysisStatusResponse(
                job_id="mock-job-id",
                status=JobStatus.COMPLETED,
                progress_percent=100,
                message="Analysis finished. Reports generated successfully.",
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{jobId}' was not found."
        )
        
    job = mock_jobs_db[jobId]
    
    # Increment progress on each request to simulate agent activity in real-time
    if job["status"] == JobStatus.PROCESSING:
        if job["progress_percent"] < 90:
            job["progress_percent"] += 25
            if 40 <= job["progress_percent"] < 65:
                job["message"] = "COB Agent resolving rules for primary/secondary insurance..."
            elif job["progress_percent"] >= 65:
                job["message"] = "Finance Agent calculating out-of-pocket costs..."
        else:
            job["progress_percent"] = 100
            job["status"] = JobStatus.COMPLETED
            job["message"] = "Pre-authorization documents drafted. Analysis completed."
            job["completed_at"] = datetime.utcnow()
            
    return AnalysisStatusResponse(**job)

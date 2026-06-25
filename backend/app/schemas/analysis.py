from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Execution status definitions for background multi-agent runs."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStartRequest(BaseModel):
    """Input parameters to start a Coordination of Benefits analysis run."""
    config: Optional[dict] = Field(None, description="Optional agent execution parameters or overrides")


class AnalysisStartResponse(BaseModel):
    """Response payload returned when an analysis job is successfully queued."""
    job_id: str = Field(..., description="Unique UUID identifying the analysis job")
    status: JobStatus = Field(JobStatus.PENDING, description="Initial status of the task")
    created_at: datetime = Field(..., description="Timestamp when the analysis job was created")
    message: str = Field(..., description="Status update message")


class AnalysisStatusResponse(BaseModel):
    """Detailed progress indicators for a running or completed analysis job."""
    job_id: str = Field(..., description="Unique UUID identifying the analysis job")
    status: JobStatus = Field(..., description="Current status of the task")
    progress_percent: int = Field(0, ge=0, le=100, description="Completion percentage of the run")
    message: str = Field(..., description="Human-readable description of current task phase")
    created_at: datetime = Field(..., description="Timestamp when the analysis job was created")
    completed_at: Optional[datetime] = Field(None, description="Timestamp when the job finished")
    error_details: Optional[str] = Field(None, description="Error messages if the job failed")

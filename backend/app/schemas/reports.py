from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from app.schemas.medical_coding import CodingResult
from app.schemas.preauth import PreAuthLetter
from app.schemas.audio import AudioBriefing


class FinancialSummary(BaseModel):
    """Detailed financial allocation breakdown computed by the Finance Agent."""
    total_billed: float = Field(..., description="The gross charge amount billed by the medical provider")
    primary_paid: float = Field(..., description="Amount covered by the primary insurance plan")
    secondary_paid: float = Field(..., description="Amount covered by the secondary insurance plan")
    patient_responsibility: float = Field(..., description="The remaining net patient out-of-pocket amount")
    currency: str = Field("USD", description="Currency format tag")


class LetterMetadata(BaseModel):
    """Metadata detailing generated prior-authorization letter documents."""
    insurer_name: str = Field(..., description="Name of the targeted insurer company")
    generated_at: datetime = Field(..., description="Timestamp when the PDF letter was drafted")
    download_url: str = Field(..., description="Asset URL to download the drafted letter PDF")
    status: str = Field("generated", description="Compilation status of the document")


class AudioMetadata(BaseModel):
    """Metadata detailing the text-to-speech coordination summary audio file."""
    duration_seconds: float = Field(..., description="Length of the audio playback file in seconds")
    generated_at: datetime = Field(..., description="Timestamp when the audio was synthesized")
    download_url: str = Field(..., description="Asset URL to stream or download the audio summary file")


class TraceEntrySchema(BaseModel):
    """Execution trace step representation."""
    agent_name: str = Field(..., description="Name of the specialist agent executing the step")
    status: str = Field(..., description="Step execution outcome, e.g., 'success', 'retry', 'error'")
    message: str = Field(..., description="Descriptive status details or exception logging")
    timestamp: str = Field(..., description="ISO timestamp of the event")


class ReportSummaryResponse(BaseModel):
    """Consolidated benefit coordination report details and download links."""
    job_id: str = Field(..., description="The UUID of the analysis run this report matches")
    patient_name: str = Field(..., description="The patient name resolved by intake parsing")
    financial_summary: FinancialSummary = Field(..., description="Calculated financial coverage details")
    preauth_letters: List[LetterMetadata] = Field(..., description="List of generated prior-authorization letters")
    audio_summary: AudioMetadata = Field(..., description="Synth audio summaries details")
    completed_at: datetime = Field(..., description="Timestamp when the report was completed")
    
    # Complete Workflow Results
    workflow_summary: Dict[str, bool] = Field(..., description="Adjudication timeline step checklist")
    trace: List[TraceEntrySchema] = Field(..., description="Execution timeline logs per agent")
    coding_result: Optional[CodingResult] = Field(None, description="Diagnostic and procedural medical codes")
    warnings: List[str] = Field(default_factory=list, description="Reviewer validation warnings")
    letters: List[PreAuthLetter] = Field(default_factory=list, description="Rendered markdown pre-authorization letters content")
    audio_briefing: Optional[AudioBriefing] = Field(None, description="Structured patient audio briefing summary narration")



from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


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


class ReportSummaryResponse(BaseModel):
    """Consolidated benefit coordination report details and download links."""
    job_id: str = Field(..., description="The UUID of the analysis run this report matches")
    patient_name: str = Field(..., description="The patient name resolved by intake parsing")
    financial_summary: FinancialSummary = Field(..., description="Calculated financial coverage details")
    preauth_letters: List[LetterMetadata] = Field(..., description="List of generated prior-authorization letters")
    audio_summary: AudioMetadata = Field(..., description="Synth audio summaries details")
    completed_at: datetime = Field(..., description="Timestamp when the report was completed")

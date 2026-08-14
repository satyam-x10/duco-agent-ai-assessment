from typing import List
from pydantic import BaseModel, Field


class AudioSection(BaseModel):
    """A single section of the spoken patient summary narration."""
    title: str = Field(..., description="The title of this section (e.g. Greeting, Summary, Insurance, Financial Summary, Pre-Authorization, Closing)")
    text: str = Field(..., description="The spoken narration text for this section, optimized for text-to-speech conversion")


class AudioBriefing(BaseModel):
    """The complete structured patient audio briefing summary narration."""
    patient_name: str = Field(..., description="The full name of the patient")
    sections: List[AudioSection] = Field(..., description="Chronological sections of the audio summary")
    full_narration: str = Field(..., description="The compiled, seamless narration text of all sections combined")
    estimated_duration_seconds: float = Field(..., description="Estimated duration of the spoken summary in seconds")


class AudioResponse(BaseModel):
    """Root response detailing generated patient briefings for a claim."""
    claim_id: str = Field(..., description="The unique claim ID matching the adjudication run")
    briefing: AudioBriefing = Field(..., description="Details of the generated audio briefing narration")
    generated_at: str = Field(..., description="ISO creation timestamp of the briefing")

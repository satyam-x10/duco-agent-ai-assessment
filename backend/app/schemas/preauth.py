from typing import List
from pydantic import BaseModel, Field


class PreAuthLetter(BaseModel):
    """Structured details of a single generated pre-authorization request letter."""
    insurer_name: str = Field(..., description="Name of the target insurance provider")
    policy_id: str = Field(..., description="The policy ID matching the insurer plan")
    patient_name: str = Field(..., description="Full name of the patient")
    letter_content: str = Field(..., description="The rendered Markdown pre-authorization letter content")
    generated_at: str = Field(..., description="ISO creation timestamp of the letter")


class PreAuthResponse(BaseModel):
    """Aggregated output containing all generated letters for a specific claim review run."""
    claim_id: str = Field(..., description="Claim identifier associated with the request")
    letters: List[PreAuthLetter] = Field(default_factory=list, description="Roster of generated pre-authorization letters")

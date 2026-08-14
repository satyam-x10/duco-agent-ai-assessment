from typing import List, Optional
from pydantic import BaseModel, Field


class ClaimLine(BaseModel):
    """A single procedure line item in a medical claim."""
    cpt_code: str = Field(..., description="The CPT procedure code (e.g., 97161)")
    billed_amount: float = Field(..., description="The original billed charge for this procedure")


class Claim(BaseModel):
    """A medical claim detailing procedures billed for a member."""
    claim_id: str = Field(..., description="Unique claim identifier")
    member_id: str = Field(..., description="The member ID of the patient (may match primary subscriber or dependent)")
    lines: List[ClaimLine] = Field(..., description="List of line items on the claim")
    diagnoses: List[str] = Field(default_factory=list, description="Extracted ICD-10 diagnosis codes supporting the claim")


class PrimaryCoverage(BaseModel):
    """Details the adjudication result of the primary insurer."""
    policy_id: str = Field(..., description="Policy ID of the primary insurer")
    is_covered: bool = Field(..., description="Whether the CPT code was covered by the primary plan")
    allowed_amount: Optional[float] = Field(None, description="Plan contractual allowed amount")
    contractual_writeoff: float = Field(0.0, description="Provider discount or write-off amount")
    copay_applied: float = Field(0.0, description="Copay amount applied to the line")
    deductible_applied: float = Field(..., description="Amount of primary deductible applied to this line")
    coinsurance_rate: float = Field(..., description="Coinsurance percentage rate responsibility of the patient")
    coinsurance_amount: float = Field(..., description="Coinsurance dollar amount billed to the patient")
    primary_paid: float = Field(..., description="Amount paid by the primary insurer")
    patient_responsibility: float = Field(..., description="Patient responsibility remaining after primary payment")


class SecondaryCoverage(BaseModel):
    """Details the coordination result of the secondary insurer."""
    policy_id: str = Field(..., description="Policy ID of the secondary insurer (empty string if no secondary)")
    is_covered: bool = Field(..., description="Whether the CPT code was covered by the secondary plan")
    allowed_amount: Optional[float] = Field(None, description="Secondary plan allowed amount")
    copay_applied: float = Field(0.0, description="Secondary copay amount applied")
    deductible_applied: float = Field(..., description="Amount of secondary deductible applied/satisfied by this line")
    coinsurance_rate: float = Field(..., description="Coinsurance percentage rate of the secondary policy")
    coinsurance_amount: float = Field(..., description="Secondary coinsurance amount calculation")
    secondary_paid: float = Field(..., description="Amount paid by the secondary insurer")
    patient_responsibility: float = Field(..., description="Patient responsibility remaining after secondary coordination")


class RemainingBalance(BaseModel):
    """Summary of final line item financial allocations."""
    billed_amount: float = Field(..., description="Original billed charge")
    primary_paid: float = Field(..., description="Final payment amount from primary")
    secondary_paid: float = Field(..., description="Final payment amount from secondary")
    patient_responsibility: float = Field(..., description="Final out-of-pocket patient responsibility")
    notes: Optional[str] = Field(None, description="Detailed explanation of the calculations or limits applied")


class ClaimLineCoverage(BaseModel):
    """Adjudication details for a single claim line under dual-coverage rules."""
    cpt_code: str = Field(..., description="CPT procedure code")
    billed_amount: float = Field(..., description="Billed charge")
    primary_coverage: PrimaryCoverage = Field(..., description="Adjudication details under the primary policy")
    secondary_coverage: SecondaryCoverage = Field(..., description="Coordination details under the secondary policy")
    remaining_balance: RemainingBalance = Field(..., description="Final summary balance representation")


class COBDecision(BaseModel):
    """The aggregate Coordination of Benefits decision result for a full claim."""
    claim_id: str = Field(..., description="Claim ID")
    patient_name: str = Field(..., description="Full name of the patient")
    primary_policy_id: Optional[str] = Field(None, description="Resolved primary policy ID")
    primary_provider: Optional[str] = Field(None, description="Resolved primary provider name")
    secondary_policy_id: Optional[str] = Field(None, description="Resolved secondary policy ID")
    secondary_provider: Optional[str] = Field(None, description="Resolved secondary provider name")
    lines_coverage: List[ClaimLineCoverage] = Field(default_factory=list, description="Calculated line item breakdowns")
    total_billed: float = Field(..., description="Sum of original billed amounts")
    total_primary_paid: float = Field(..., description="Sum of payments by primary")
    total_secondary_paid: float = Field(..., description="Sum of payments by secondary")
    total_patient_responsibility: float = Field(..., description="Sum of final patient out-of-pocket responsibility")

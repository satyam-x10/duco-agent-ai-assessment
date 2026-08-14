from typing import List, Optional
from pydantic import BaseModel, Field


class ClaimLine(BaseModel):
    """A single procedure line item in a medical claim."""
    cpt_code: str = Field(..., description="The CPT procedure code (e.g., 97161)")
    billed_amount: float = Field(..., description="The original billed charge for this procedure")
    member_id: Optional[str] = Field(None, description="Member receiving the service")
    patient_name: Optional[str] = Field(None, description="Patient receiving the service")
    diagnoses: List[str] = Field(default_factory=list, description="Diagnoses supporting this line")
    source_document: Optional[str] = Field(None, description="Document slot that supplied the charge")
    source_evidence: Optional[str] = Field(None, description="Extracted source snippet supporting the charge")
    amount_source: str = Field("explicit_line", description="How the line amount was obtained")


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
    deductible_applied: float = Field(0.0, description="Amount of primary deductible applied to this line")
    coinsurance_rate: float = Field(0.0, description="Coinsurance percentage rate responsibility of the patient")
    coinsurance_amount: float = Field(0.0, description="Coinsurance dollar amount billed to the patient")
    primary_paid: float = Field(0.0, description="Amount paid by the primary insurer")
    patient_responsibility: float = Field(0.0, description="Patient responsibility remaining after primary payment")


class SecondaryCoverage(BaseModel):
    """Details the coordination result of the secondary insurer."""
    policy_id: str = Field(..., description="Policy ID of the secondary insurer (empty string if no secondary)")
    is_covered: bool = Field(..., description="Whether the CPT code was covered by the secondary plan")
    allowed_amount: Optional[float] = Field(None, description="Secondary plan allowed amount")
    copay_applied: float = Field(0.0, description="Secondary copay amount applied")
    deductible_applied: float = Field(0.0, description="Amount of secondary deductible applied/satisfied by this line")
    coinsurance_rate: float = Field(0.0, description="Coinsurance percentage rate of the secondary policy")
    coinsurance_amount: float = Field(0.0, description="Secondary coinsurance amount calculation")
    secondary_paid: float = Field(0.0, description="Amount paid by the secondary insurer")
    patient_responsibility: float = Field(0.0, description="Patient responsibility remaining after secondary coordination")


class RemainingBalance(BaseModel):
    """Summary of final line item financial allocations."""
    billed_amount: float = Field(0.0, description="Original billed charge")
    primary_paid: float = Field(0.0, description="Final payment amount from primary")
    secondary_paid: float = Field(0.0, description="Final payment amount from secondary")
    patient_responsibility: float = Field(0.0, description="Final out-of-pocket patient responsibility")
    notes: Optional[str] = Field(None, description="Detailed explanation of the calculations or limits applied")
    is_satisfied: bool = Field(True, description="Whether the balance is settled across insurers and patient")


class ClaimLineCoverage(BaseModel):
    """Adjudication details for a single claim line under dual-coverage rules."""
    cpt_code: str = Field(..., description="CPT procedure code")
    billed_amount: float = Field(..., description="Billed charge")
    member_id: Optional[str] = Field(None, description="Member adjudicated on this line")
    patient_name: Optional[str] = Field(None, description="Patient adjudicated on this line")
    source_document: Optional[str] = Field(None, description="Source document for the billed amount")
    primary_coverage: PrimaryCoverage = Field(..., description="Adjudication details under the primary policy")
    secondary_coverage: SecondaryCoverage = Field(..., description="Coordination details under the secondary policy")
    remaining_balance: RemainingBalance = Field(..., description="Final summary balance representation")


class PatientClaimSummary(BaseModel):
    """Patient-specific totals retained when a family workflow contains multiple claims."""
    member_id: str
    patient_name: str
    primary_policy_id: Optional[str] = None
    secondary_policy_id: Optional[str] = None
    total_billed: float
    total_primary_paid: float
    total_secondary_paid: float
    total_patient_responsibility: float


class COBDecision(BaseModel):
    """The aggregate Coordination of Benefits decision result for a full claim."""
    claim_id: str = Field(..., description="Claim ID")
    patient_name: str = Field(..., description="Full name of the patient")
    primary_policy_id: str = Field(..., description="Primary policy ID determined by COB rules")
    primary_provider: Optional[str] = Field(None, description="Name of the primary insurance provider")
    secondary_policy_id: Optional[str] = Field(None, description="Secondary policy ID (if dual coverage exists)")
    secondary_provider: Optional[str] = Field(None, description="Name of the secondary insurance provider")
    lines_coverage: List[ClaimLineCoverage] = Field(default_factory=list, description="Per-line breakdown of COB decisions")
    total_billed: float = Field(..., description="Aggregated billed amount across all lines")
    total_primary_paid: float = Field(..., description="Aggregated primary payout across all lines")
    total_secondary_paid: float = Field(..., description="Aggregated secondary payout across all lines")
    total_patient_responsibility: float = Field(..., description="Aggregated out-of-pocket patient responsibility")
    patient_claims: List[PatientClaimSummary] = Field(default_factory=list, description="Patient-level breakdown when multiple family claims exist")
    is_fully_adjudicated: bool = Field(True, description="Whether all lines passed adjudication successfully")

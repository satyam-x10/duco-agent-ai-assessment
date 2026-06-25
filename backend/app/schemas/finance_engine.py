from typing import List, Optional
from pydantic import BaseModel, Field


class PaymentAllocation(BaseModel):
    """Detailed procedure-level payment allocation for insurer and patient responsibilities."""
    cpt_code: str = Field(..., description="CPT procedure code")
    billed_amount: float = Field(..., description="Billed charge amount for the procedure")
    primary_paid: float = Field(..., description="Amount paid by the primary insurer")
    secondary_paid: float = Field(..., description="Amount paid by the secondary insurer")
    patient_deductible_applied: float = Field(..., description="Portion of patient responsibility applied to the deductible")
    patient_coinsurance_applied: float = Field(..., description="Portion of patient responsibility applied to coinsurance")
    patient_responsibility: float = Field(..., description="Total out-of-pocket patient responsibility for this procedure")


class PatientResponsibility(BaseModel):
    """Aggregated patient responsibility detail showing deductible vs coinsurance splits."""
    total_deductible: float = Field(..., description="Total deductible amount the patient must pay")
    total_coinsurance: float = Field(..., description="Total coinsurance amount the patient must pay")
    total_responsibility: float = Field(..., description="Total out-of-pocket patient responsibility")
    explanation_notes: str = Field(..., description="Detailed explanation of the final out-of-pocket calculations")


class CostSummary(BaseModel):
    """Aggregated claim-level summary of financial allocations and savings."""
    total_billed: float = Field(..., description="Total billed charge amount across all procedures")
    total_primary_paid: float = Field(..., description="Total amount paid by the primary insurer")
    total_secondary_paid: float = Field(..., description="Total amount paid by the secondary insurer")
    total_insurer_paid: float = Field(..., description="Total combined insurer payments (primary + secondary)")
    total_patient_responsibility: float = Field(..., description="Total combined out-of-pocket patient responsibility")
    total_savings: float = Field(..., description="Total savings for the patient (total billed minus final responsibility)")


class FinancialBreakdown(BaseModel):
    """Unified financial breakdown containing summary, responsibility details, and item allocations."""
    allocations: List[PaymentAllocation] = Field(default_factory=list, description="Procedure-level allocation details")
    patient_responsibility: PatientResponsibility = Field(..., description="Out-of-pocket patient responsibility details")
    summary: CostSummary = Field(..., description="Claim-level cost summaries")


class FinancialReport(BaseModel):
    """Highest-level financial report representing the complete adjudicated and audited ledger."""
    report_id: str = Field(..., description="Unique report identifier")
    claim_id: str = Field(..., description="Claim ID associated with the breakdown")
    patient_name: str = Field(..., description="Full name of the patient")
    generated_at: str = Field(..., description="ISO timestamp representing report generation time")
    primary_policy_id: Optional[str] = Field(None, description="Resolved primary policy ID")
    secondary_policy_id: Optional[str] = Field(None, description="Resolved secondary policy ID")
    breakdown: FinancialBreakdown = Field(..., description="Adjudicated financial details")

from typing import List, Optional
from pydantic import BaseModel, Field


class Member(BaseModel):
    """Individual policyholder or dependent details."""
    member_id: str = Field(..., description="Unique member identifier or family subscriber ID")
    first_name: str = Field(..., description="First name of the member")
    last_name: str = Field(..., description="Last name of the member")
    role: str = Field(..., description="Role in policy, e.g., 'subscriber' or 'dependent'")
    relationship_to_subscriber: str = Field(..., description="Relationship to primary subscriber, e.g., 'self', 'spouse', 'child'")
    date_of_birth: str = Field(..., description="Date of birth in YYYY-MM-DD format")


class Deductible(BaseModel):
    """Tracks total and remaining deductible balances for individual and family."""
    individual: float = Field(..., description="Total individual deductible threshold")
    family: float = Field(..., description="Total family deductible threshold")
    remaining_individual: float = Field(..., description="Remaining individual deductible amount")
    remaining_family: float = Field(..., description="Remaining family deductible amount")


class Coinsurance(BaseModel):
    """Coinsurance responsibility rate details."""
    rate: float = Field(..., description="The percentage rate the patient pays after deductible (e.g., 0.20 for 20%)")


class CoverageRule(BaseModel):
    """Specific rule for procedure code (CPT) coverage bounds."""
    cpt_code: str = Field(..., description="The CPT procedure code (e.g., 97161)")
    is_covered: bool = Field(..., description="Whether this procedure is covered under the policy")
    requires_preauth: bool = Field(..., description="Whether pre-authorization is required for this CPT code")
    limitations: Optional[str] = Field(None, description="Optional text describing coverage limitations or requirements")


class InsurancePolicy(BaseModel):
    """The aggregate insurance policy schema containing limits, members, and coverage rules."""
    policy_id: str = Field(..., description="Unique policy identifier")
    provider_name: str = Field(..., description="Name of the insurance provider")
    group_number: str = Field(..., description="Group policy number")
    deductible: Deductible = Field(..., description="Deductible configuration")
    coinsurance: Coinsurance = Field(..., description="Coinsurance configuration")
    out_of_pocket_max: float = Field(..., description="Out of pocket maximum threshold")
    remaining_out_of_pocket_max: float = Field(..., description="Remaining out of pocket maximum balance")
    members: List[Member] = Field(default_factory=list, description="List of members covered under this policy")
    coverage_rules: List[CoverageRule] = Field(default_factory=list, description="Coverage guidelines mapped by CPT code")


class CoverageDecision(BaseModel):
    """Result details for a coverage evaluation of a specific procedure."""
    is_covered: bool = Field(..., description="Whether the CPT code is covered")
    requires_preauth: bool = Field(..., description="Whether pre-authorization is required")
    deductible_applies: bool = Field(..., description="Whether the deductible applies to this procedure")
    coinsurance_rate: float = Field(..., description="The patient responsibility coinsurance rate")
    message: str = Field(..., description="Clinical or administrative explanation details")

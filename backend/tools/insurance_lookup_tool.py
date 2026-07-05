import logging
from typing import Optional, List
from app.schemas.insurance_engine import InsurancePolicy, Member, CoverageDecision
from services.insurance_engine import InsuranceService

logger = logging.getLogger(__name__)

class InsuranceLookupTool:
    """Tool used by agents to query policies, member information, and check coverage eligibility."""
    
    def __init__(self, insurance_service: InsuranceService):
        self.name = "InsuranceLookupTool"
        self.description = "Queries active policy schemas, subscriber status, and maps coverage rules."
        self.insurance_service = insurance_service

    def get_member(self, member_id: str) -> Optional[Member]:
        """Looks up member info by ID."""
        logger.info(f"[{self.name}] Querying member details for ID: {member_id}")
        return self.insurance_service.get_member(member_id)

    def evaluate_coverage(self, member_id: str, cpt_code: str) -> CoverageDecision:
        """Determines detailed coverage eligibility, pre-auth rules, and patient rates."""
        logger.info(f"[{self.name}] Evaluating coverage for member {member_id} and CPT {cpt_code}")
        return self.insurance_service.evaluate_coverage(member_id, cpt_code)

    def get_all_policies(self) -> List[InsurancePolicy]:
        """Returns all loaded active policy models."""
        return list(self.insurance_service._policies.values())

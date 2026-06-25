import logging
from app.core.adk import Agent, SharedWorkflowState
from app.schemas.cob_engine import Claim, ClaimLine
from services.cob_engine import COBEngine

logger = logging.getLogger(__name__)

# Typical billed amounts matching the assessment scenarios
CPT_BILLED_AMOUNTS = {
    "97161": 650.00,  # Physical Therapy Evaluation
    "97110": 200.00,  # Therapeutic Exercises
    "73721": 1200.00, # MRI Joint Lower Extremity (Aarav MRI)
    "29881": 8900.00, # Meniscectomy Arthroscopy (Aarav Surgery)
    "29888": 15000.00 # ACL reconstruction
}


class COBAgent(Agent):
    """Specialist agent coordinating the benefit determinations and insurer payment order resolution."""

    def __init__(self, cob_engine: COBEngine):
        super().__init__("COBAgent")
        self.cob_engine = cob_engine

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} coordinating benefits for claim {state.claim_id}")
        
        if not state.coding_result or not state.coding_result.procedures:
            raise ValueError("No procedure codes have been extracted. COB coordination cannot proceed.")
            
        # Build claim lines with realistic billed amounts
        claim_lines = []
        for procedure in state.coding_result.procedures:
            billed_amount = CPT_BILLED_AMOUNTS.get(procedure.code, 500.00)
            claim_lines.append(ClaimLine(cpt_code=procedure.code, billed_amount=billed_amount))
            
        # Construct Claim
        claim = Claim(
            claim_id=f"CLAIM-{state.claim_id}",
            member_id=state.member_id,
            lines=claim_lines
        )
        
        # Run benefits coordination
        cob_decision = self.cob_engine.coordinate_benefits(claim)
        
        state.cob_decision = cob_decision
        
        # Sync final resolved primary/secondary policies in state
        if cob_decision.primary_policy_id:
            state.primary_policy = self.cob_engine.insurance_service._policies.get(cob_decision.primary_policy_id)
        if cob_decision.secondary_policy_id:
            state.secondary_policy = self.cob_engine.insurance_service._policies.get(cob_decision.secondary_policy_id)
            
        logger.info(
            f"{self.name} completed coordination. Primary: {cob_decision.primary_policy_id}, "
            f"Secondary: {cob_decision.secondary_policy_id or 'None'}. Billed total: ${cob_decision.total_billed:.2f}"
        )

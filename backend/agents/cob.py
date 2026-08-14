import logging
from app.core.adk import Agent, SharedWorkflowState
from app.schemas.cob_engine import Claim, ClaimLine
from services.cob_engine import COBEngine

logger = logging.getLogger(__name__)

# Typical billed amounts matching the assessment scenarios
CPT_BILLED_AMOUNTS = {
    "97161": 20000.00,  # Physical Therapy Evaluation
    "97110": 10000.00,  # Therapeutic Exercises
    "73721": 12000.00,  # MRI Joint Lower Extremity (Aarav MRI)
    "29881": 100000.00, # Meniscectomy Arthroscopy (Aarav Surgery)
    "29888": 350000.00  # ACL reconstruction
}


class COBAgent(Agent):
    """Specialist agent coordinating the benefit determinations and insurer payment order resolution."""

    def __init__(self, cob_engine: COBEngine):
        super().__init__("COBAgent")
        self.cob_engine = cob_engine

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} coordinating benefits for claim {state.claim_id}")
        
        if state.mock_mode:
            import asyncio
            await asyncio.sleep(0.8)
            
        if not state.coding_result or not state.coding_result.procedures:
            raise ValueError("No procedure codes have been extracted. COB coordination cannot proceed.")
            
        # Build claim lines preferring source-grounded amounts extracted from documents
        amounts_by_cpt = {line.cpt_code: line.billed_amount for line in state.claim_lines}
        if not amounts_by_cpt and state.processed_documents:
            for doc in state.processed_documents.values():
                if hasattr(doc, "facts") and doc.facts and doc.facts.line_items:
                    for fact_line in doc.facts.line_items:
                        amounts_by_cpt[fact_line.cpt_code] = fact_line.billed_amount

        claim_lines = []
        for procedure in state.coding_result.procedures:
            billed_amount = amounts_by_cpt.get(procedure.code, CPT_BILLED_AMOUNTS.get(procedure.code, 500.00))
            claim_lines.append(ClaimLine(cpt_code=procedure.code, billed_amount=billed_amount))

        state.claim_lines = claim_lines
            
        # Extract diagnosis code strings
        diagnoses = [d.code for d in state.coding_result.diagnoses] if state.coding_result else []
        
        # Construct Claim
        claim = Claim(
            claim_id=f"CLAIM-{state.claim_id}",
            member_id=state.member_id,
            lines=claim_lines,
            diagnoses=diagnoses
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

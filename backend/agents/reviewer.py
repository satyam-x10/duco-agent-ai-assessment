import logging
from app.core.adk import Agent, SharedWorkflowState

logger = logging.getLogger(__name__)


class ReviewerAgent(Agent):
    """Specialist agent responsible for validating pipeline outputs, structural completeness, and quality warning checks."""

    def __init__(self):
        super().__init__("ReviewerAgent")

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} auditing workflow outputs for claim {state.claim_id}")
        
        # 1. Verify existence of primary artifacts
        if not state.financial_report:
            raise ValueError("Structural audit failed: Financial report is missing.")
            
        if not state.cob_decision:
            raise ValueError("Structural audit failed: COB benefits decision is missing.")
            
        # 2. Check for missing metadata info
        if not state.financial_report.patient_name:
            state.warnings.append("Warning: Patient name is blank in the financial report.")
            
        if not state.financial_report.primary_policy_id:
            state.warnings.append("Warning: Primary insurance policy identifier is missing.")
            
        # 3. Audit confidence levels of extracted clinical codes
        if state.coding_result:
            for diagnosis in state.coding_result.diagnoses:
                if diagnosis.confidence < 0.70:
                    warn_msg = f"Low confidence diagnosis code extraction: {diagnosis.code} (confidence: {diagnosis.confidence:.2f})"
                    state.warnings.append(warn_msg)
                    logger.warning(warn_msg)
                    
            for procedure in state.coding_result.procedures:
                if procedure.confidence < 0.70:
                    warn_msg = f"Low confidence procedure code extraction: {procedure.code} (confidence: {procedure.confidence:.2f})"
                    state.warnings.append(warn_msg)
                    logger.warning(warn_msg)
                    
        # 4. Check for lack of secondary insurance
        if not state.financial_report.secondary_policy_id:
            state.warnings.append("Note: Claim processed under single coverage; no secondary insurance resolved.")
            
        logger.info(f"{self.name} completed validation audit. Generated {len(state.warnings)} warning indicators.")

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
            
        # 5. Audit Logical Inconsistencies (Rule 5)
        # A. Patient name mismatch between policy subscriber and clinical records
        p_member = None
        if state.primary_policy:
            for m in state.primary_policy.members:
                if m.member_id == state.member_id:
                    p_member = m
                    break
            
            if p_member:
                name_found = False
                for doc in state.processed_documents.values():
                    if p_member.first_name.lower() in doc.extracted_text.lower() or p_member.last_name.lower() in doc.extracted_text.lower():
                        name_found = True
                        break
                if not name_found:
                    state.warnings.append(f"[Policy Inconsistency] Resolved patient name '{p_member.first_name} {p_member.last_name}' does not appear in any extracted clinical texts.")

        # B. Name mismatch between primary and secondary policies
        if state.primary_policy and state.secondary_policy and p_member:
            s_member = None
            for m in state.secondary_policy.members:
                if m.date_of_birth == p_member.date_of_birth:
                    s_member = m
                    break
            if s_member and (s_member.first_name.lower() != p_member.first_name.lower() or s_member.last_name.lower() != p_member.last_name.lower()):
                state.warnings.append(f"[Policy Inconsistency] Patient name mismatch between insurers. Primary: {p_member.first_name} {p_member.last_name}, Secondary: {s_member.first_name} {s_member.last_name}")

        # C. Procedure-coverage or supporting diagnosis mismatch
        if state.coding_result:
            procedures = state.coding_result.procedures
            diagnoses = state.coding_result.diagnoses
            
            # Mapped CPT not covered under primary policy
            if state.primary_policy:
                for proc in procedures:
                    covered = False
                    for rule in state.primary_policy.coverage_rules:
                        if rule.cpt_code == proc.code:
                            covered = rule.is_covered
                            break
                    if not covered:
                        state.warnings.append(f"[Coding Inconsistency] Extracted procedure {proc.code} is NOT covered under primary policy {state.primary_policy.policy_id}.")
            
            # Procedures exist without supporting diagnoses
            if procedures and not diagnoses:
                state.warnings.append("[Coding Inconsistency] Extracted procedures exist but no supporting clinical diagnosis was coded.")
            
        # Check if manual human approval is required due to low confidence warnings or inconsistencies
        if any("Low confidence" in w or "Inconsistency" in w for w in state.warnings):
            state.requires_human_approval = True
            logger.info(f"{self.name} flagged workflow as requiring manual clinician audit approval.")
            
        logger.info(f"{self.name} completed validation audit. Generated {len(state.warnings)} warning indicators.")

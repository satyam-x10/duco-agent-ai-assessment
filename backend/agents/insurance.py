import logging
from app.core.adk import Agent, SharedWorkflowState
from services.insurance_engine import InsuranceService

logger = logging.getLogger(__name__)


class InsuranceAgent(Agent):
    """Specialist agent responsible for resolving and loading insurance policies matching a member ID."""

    def __init__(self, insurance_service: InsuranceService):
        super().__init__("InsuranceAgent")
        self.insurance_service = insurance_service

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} resolving policies for member ID {state.member_id}")
        
        if state.mock_mode:
            import asyncio
            await asyncio.sleep(0.8)
            
        # Resolve patient member details first using formal InsuranceLookupTool
        from tools.insurance_lookup_tool import InsuranceLookupTool
        lookup_tool = InsuranceLookupTool(self.insurance_service)
        patient_member = lookup_tool.get_member(state.member_id)
        if not patient_member:
            raise ValueError(f"Patient member with ID '{state.member_id}' not found.")
            
        # Find all policies covering this member (by name and DOB) using tool
        matched_policies = []
        for policy in lookup_tool.get_all_policies():
            for member in policy.members:
                if (
                    member.first_name.lower() == patient_member.first_name.lower()
                    and member.last_name.lower() == patient_member.last_name.lower()
                    and member.date_of_birth == patient_member.date_of_birth
                ):
                    matched_policies.append(policy)
                    break
                    
        if not matched_policies:
            raise ValueError(f"No insurance policies found covering patient {patient_member.first_name} {patient_member.last_name}.")
            
        # Associate policies to state (order will be refined by COB Engine)
        state.primary_policy = matched_policies[0]
        if len(matched_policies) > 1:
            state.secondary_policy = matched_policies[1]
            logger.info(f"{self.name} resolved dual coverage policies: {state.primary_policy.policy_id} and {state.secondary_policy.policy_id}")
        else:
            state.secondary_policy = None
            logger.info(f"{self.name} resolved single coverage policy: {state.primary_policy.policy_id}")

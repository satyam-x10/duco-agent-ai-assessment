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
        logger.info(f"{self.name} resolving policies from extracted patient identities")
        
        if state.mock_mode:
            import asyncio
            await asyncio.sleep(0.8)
            
        # Resolve every distinct patient found in source documents. The request
        # member_id is retained only as a compatibility fallback.
        from tools.insurance_lookup_tool import InsuranceLookupTool
        lookup_tool = InsuranceLookupTool(self.insurance_service)
        resolved_members = []
        seen_people = set()
        for document in state.processed_documents.values():
            facts = document.facts
            patient_member = lookup_tool.get_member(facts.member_id) if facts.member_id else None
            if not patient_member and facts.patient_name:
                target = facts.patient_name.strip().lower()
                for policy in lookup_tool.get_all_policies():
                    patient_member = next(
                        (m for m in policy.members if f"{m.first_name} {m.last_name}".lower() == target),
                        None,
                    )
                    if patient_member:
                        break
            if patient_member:
                person_key = (patient_member.first_name.lower(), patient_member.last_name.lower(), patient_member.date_of_birth)
                if person_key not in seen_people:
                    seen_people.add(person_key)
                    resolved_members.append(patient_member)

        if not resolved_members:
            fallback_member = lookup_tool.get_member(state.member_id)
            if fallback_member:
                resolved_members.append(fallback_member)
        if not resolved_members:
            raise ValueError("No uploaded-document patient could be matched to an active policy member.")

        state.member_ids = [member.member_id for member in resolved_members]
        state.member_id = state.member_ids[0]
        state.patient_name = " & ".join(f"{m.first_name} {m.last_name}" for m in resolved_members)
            
        # Find all policies covering this member (by name and DOB) using tool
        matched_policies = []
        for policy in lookup_tool.get_all_policies():
            for patient_member in resolved_members:
                if any(
                    member.first_name.lower() == patient_member.first_name.lower()
                    and member.last_name.lower() == patient_member.last_name.lower()
                    and member.date_of_birth == patient_member.date_of_birth
                    for member in policy.members
                ):
                    matched_policies.append(policy)
                    break
                    
        if not matched_policies:
            raise ValueError("No insurance policies cover the patients resolved from uploaded documents.")
            
        # Associate policies to state (order will be refined by COB Engine)
        state.primary_policy = matched_policies[0]
        if len(matched_policies) > 1:
            state.secondary_policy = matched_policies[1]
            logger.info(f"{self.name} resolved dual coverage policies: {state.primary_policy.policy_id} and {state.secondary_policy.policy_id}")
        else:
            state.secondary_policy = None
            logger.info(f"{self.name} resolved single coverage policy: {state.primary_policy.policy_id}")

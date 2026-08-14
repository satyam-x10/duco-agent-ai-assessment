import logging
from datetime import datetime
from typing import Dict, List, Tuple

from app.core.adk import SharedWorkflowState
from app.schemas.preauth import PreAuthLetter, PreAuthResponse

logger = logging.getLogger(__name__)


class PreAuthorizationService:
    """Generate source-grounded clinician-review drafts for required procedures only."""

    @staticmethod
    def _line_is_eligible(state: SharedWorkflowState, cpt_code: str, member_id: str) -> bool:
        if not state.cob_decision:
            return False
        for line in state.cob_decision.lines_coverage:
            if line.cpt_code == cpt_code and line.member_id == member_id:
                notes = (line.remaining_balance.notes or "").lower()
                return "not medically necessary" not in notes and "manual clinical review" not in notes
        return False

    @staticmethod
    def _patient_on_policy(policy, member_id: str, patient_name: str):
        direct = next((member for member in policy.members if member.member_id == member_id), None)
        if direct:
            return direct
        target = patient_name.lower()
        return next(
            (member for member in policy.members if f"{member.first_name} {member.last_name}".lower() == target),
            None,
        )

    def generate_letters(self, state: SharedWorkflowState) -> PreAuthResponse:
        if not state.claim_lines:
            return PreAuthResponse(claim_id=state.claim_id, letters=[])

        policies = [policy for policy in (state.primary_policy, state.secondary_policy) if policy]
        procedure_descriptions = {
            procedure.code: procedure.description
            for procedure in (state.coding_result.procedures if state.coding_result else [])
        }

        # Each patient gets a separate request under each policy. Combining
        # family members in one clinical letter is unsafe and confusing.
        requests: Dict[Tuple[str, str], dict] = {}
        for policy in policies:
            rules = {rule.cpt_code: rule for rule in policy.coverage_rules}
            for claim_line in state.claim_lines:
                rule = rules.get(claim_line.cpt_code)
                if not rule or not rule.requires_preauth:
                    continue
                if not claim_line.member_id or not claim_line.patient_name:
                    continue
                if not self._line_is_eligible(state, claim_line.cpt_code, claim_line.member_id):
                    continue
                member = self._patient_on_policy(
                    policy, claim_line.member_id, claim_line.patient_name
                )
                if not member:
                    continue
                key = (policy.policy_id, claim_line.patient_name)
                request = requests.setdefault(
                    key,
                    {"policy": policy, "member": member, "patient_name": claim_line.patient_name, "lines": []},
                )
                request["lines"].append(claim_line)

        letters: List[PreAuthLetter] = []
        generated_at = datetime.utcnow().isoformat() + "Z"
        generated_date = datetime.utcnow().strftime("%B %d, %Y")

        for request in requests.values():
            policy = request["policy"]
            member = request["member"]
            patient_name = request["patient_name"]
            claim_lines = request["lines"]

            diagnoses = sorted({diagnosis for line in claim_lines for diagnosis in line.diagnoses})
            source_documents = sorted({line.source_document for line in claim_lines if line.source_document})

            providers = []
            for document_type, document in state.processed_documents.items():
                facts = document.facts
                if facts.patient_name and facts.patient_name.lower() == patient_name.lower():
                    provider = facts.provider
                    if provider.name or provider.npi or provider.facility:
                        providers.append(provider)
            provider = providers[0] if providers else None
            provider_name = provider.name if provider and provider.name else "Not documented - clinician completion required"
            provider_npi = provider.npi if provider and provider.npi else "Not documented - clinician completion required"
            facility = provider.facility if provider and provider.facility else "Not documented - clinician completion required"

            rows = []
            for line in claim_lines:
                description = procedure_descriptions.get(line.cpt_code, "Procedure documented in source")
                rows.append(
                    f"| `{line.cpt_code}` | {description} | INR {line.billed_amount:,.2f} | {line.source_document or 'Unknown'} |"
                )
            total = sum(line.billed_amount for line in claim_lines)
            diagnoses_text = ", ".join(diagnoses) if diagnoses else "Not documented - clinician review required"
            sources_text = ", ".join(source_documents) if source_documents else "No source document resolved"

            content = f"""# PRIOR AUTHORIZATION REQUEST - DRAFT FOR CLINICIAN REVIEW

**Date:** {generated_date}
**To:** Prior Authorization Department, {policy.provider_name}

> This draft is generated from uploaded source documents. A licensed clinician must verify, complete, and sign it before submission.

## Patient and policy

- **Patient:** {patient_name}
- **Date of birth:** {member.date_of_birth}
- **Member ID:** {member.member_id}
- **Policy / plan:** {policy.policy_id}
- **Group number:** {policy.group_number}

## Requesting provider

- **Provider:** {provider_name}
- **NPI:** {provider_npi}
- **Facility:** {facility}

## Procedures requiring authorization under this plan

| CPT | Description | Source-grounded billed amount | Evidence source |
| --- | --- | ---: | --- |
{chr(10).join(rows)}

**Total requested amount:** INR {total:,.2f}

## Clinical evidence

- **Documented diagnosis codes:** {diagnoses_text}
- **Source documents reviewed:** {sources_text}
- No symptoms, examination findings, failed therapies, or clinical conclusions have been added unless present in the uploaded evidence.

## Clinician attestation

I have reviewed this draft against the patient's medical record and attest that the requested services are medically necessary and accurately represented.

**Clinician name:** ____________________
**Signature:** ____________________
**Date:** ____________________
"""
            letters.append(
                PreAuthLetter(
                    insurer_name=policy.provider_name,
                    policy_id=policy.policy_id,
                    patient_name=patient_name,
                    letter_content=content,
                    generated_at=generated_at,
                )
            )

        logger.info("Generated %s source-grounded preauthorization draft(s)", len(letters))
        return PreAuthResponse(claim_id=state.claim_id, letters=letters)

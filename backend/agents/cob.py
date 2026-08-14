import logging
from collections import defaultdict

from app.core.adk import Agent, FatalBusinessError, SharedWorkflowState
from app.schemas.cob_engine import COBDecision, Claim, ClaimLine
from services.cob_engine import COBEngine

logger = logging.getLogger(__name__)


class COBAgent(Agent):
    """Builds patient-specific, source-grounded claims and coordinates each one."""

    def __init__(self, cob_engine: COBEngine):
        super().__init__("COBAgent")
        self.cob_engine = cob_engine

    def _resolve_member_id(self, patient_name: str | None, supplied_member_id: str | None) -> str | None:
        if supplied_member_id and self.cob_engine.insurance_service.get_member(supplied_member_id):
            return supplied_member_id
        if not patient_name:
            return None
        normalized = patient_name.strip().lower()
        for policy in self.cob_engine.insurance_service._policies.values():
            for member in policy.members:
                if f"{member.first_name} {member.last_name}".lower() == normalized:
                    return member.member_id
        return None

    def _build_grounded_lines(self, state: SharedWorkflowState) -> list[ClaimLine]:
        diagnoses_by_member: dict[str, set[str]] = defaultdict(set)
        document_members: dict[object, str] = {}

        for document_type, document in state.processed_documents.items():
            facts = document.facts
            member_id = self._resolve_member_id(facts.patient_name, facts.member_id)
            if member_id:
                document_members[document_type] = member_id
                diagnoses_by_member[member_id].update(facts.diagnosis_codes)

        grounded_lines: list[ClaimLine] = []
        for document_type, document in state.processed_documents.items():
            member_id = document_members.get(document_type)
            if not member_id:
                if document.facts.line_items:
                    state.warnings.append(
                        f"[Grounding Inconsistency] {document_type.value} contains charges but no resolvable patient identity."
                    )
                    state.requires_human_approval = True
                continue

            patient = self.cob_engine.insurance_service.get_member(member_id)
            patient_name = f"{patient.first_name} {patient.last_name}" if patient else document.facts.patient_name
            diagnoses = sorted(diagnoses_by_member.get(member_id, set()))
            for fact_line in document.facts.line_items:
                grounded_lines.append(
                    ClaimLine(
                        cpt_code=fact_line.cpt_code,
                        billed_amount=fact_line.billed_amount,
                        member_id=member_id,
                        patient_name=patient_name,
                        diagnoses=diagnoses,
                        source_document=document_type.value,
                        source_evidence=fact_line.evidence,
                        amount_source=fact_line.amount_source,
                    )
                )
                if fact_line.amount_source != "explicit_line":
                    state.warnings.append(
                        f"[Grounding Inconsistency] CPT {fact_line.cpt_code} amount was {fact_line.amount_source}; clinician verification is required."
                    )
                    state.requires_human_approval = True

        extracted_codes = {
            procedure.code for procedure in state.coding_result.procedures
        } if state.coding_result else set()
        grounded_codes = {line.cpt_code for line in grounded_lines}
        for code in sorted(extracted_codes - grounded_codes):
            state.warnings.append(
                f"[Grounding Inconsistency] CPT {code} was extracted but has no source-grounded billed amount; it was not adjudicated."
            )
            state.requires_human_approval = True

        if not grounded_lines:
            raise FatalBusinessError(
                "No source-grounded CPT charge lines were extracted. Adjudication refuses to substitute fixed prices."
            )
        return grounded_lines

    def coordinate_state(self, state: SharedWorkflowState) -> None:
        if not state.coding_result or not state.coding_result.procedures:
            raise FatalBusinessError("No procedure codes were extracted; COB coordination cannot proceed.")

        grounded_lines = self._build_grounded_lines(state)
        state.claim_lines = grounded_lines
        lines_by_member: dict[str, list[ClaimLine]] = defaultdict(list)
        for line in grounded_lines:
            if not line.member_id:
                raise FatalBusinessError(f"CPT {line.cpt_code} is missing a member identifier.")
            lines_by_member[line.member_id].append(line)

        decisions: list[COBDecision] = []
        for member_id, lines in lines_by_member.items():
            diagnoses = sorted({diagnosis for line in lines for diagnosis in line.diagnoses})
            claim = Claim(
                claim_id=f"{state.claim_id}-{member_id}",
                member_id=member_id,
                lines=lines,
                diagnoses=diagnoses,
            )
            decisions.append(self.cob_engine.coordinate_benefits(claim))

        if len(decisions) == 1:
            state.cob_decision = decisions[0].model_copy(update={"claim_id": state.claim_id})
        else:
            patient_names = [decision.patient_name for decision in decisions]
            primary_ids = {decision.primary_policy_id for decision in decisions}
            secondary_ids = {decision.secondary_policy_id for decision in decisions}
            primary_providers = {decision.primary_provider for decision in decisions}
            secondary_providers = {decision.secondary_provider for decision in decisions}
            state.cob_decision = COBDecision(
                claim_id=state.claim_id,
                patient_name=" & ".join(patient_names),
                primary_policy_id=next(iter(primary_ids)) if len(primary_ids) == 1 else None,
                primary_provider=next(iter(primary_providers)) if len(primary_providers) == 1 else "Multiple primary payers",
                secondary_policy_id=next(iter(secondary_ids)) if len(secondary_ids) == 1 else None,
                secondary_provider=next(iter(secondary_providers)) if len(secondary_providers) == 1 else "Multiple secondary payers",
                lines_coverage=[line for decision in decisions for line in decision.lines_coverage],
                patient_claims=[summary for decision in decisions for summary in decision.patient_claims],
                total_billed=round(sum(decision.total_billed for decision in decisions), 2),
                total_primary_paid=round(sum(decision.total_primary_paid for decision in decisions), 2),
                total_secondary_paid=round(sum(decision.total_secondary_paid for decision in decisions), 2),
                total_patient_responsibility=round(
                    sum(decision.total_patient_responsibility for decision in decisions), 2
                ),
            )

        logger.info(
            "%s coordinated %s patient claim(s) with %s grounded lines.",
            self.name,
            len(decisions),
            len(grounded_lines),
        )

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info("%s coordinating benefits for claim %s", self.name, state.claim_id)
        self.coordinate_state(state)

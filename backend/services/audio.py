import logging
from datetime import datetime
from typing import List

from app.core.adk import SharedWorkflowState
from app.schemas.audio import AudioSection, AudioBriefing, AudioResponse
from app.schemas.intake import DocumentType

logger = logging.getLogger(__name__)


class AudioBriefingService:
    """Service responsible for generating clear, patient-friendly spoken summary narrations from workflow results."""

    def generate_briefing(self, state: SharedWorkflowState) -> AudioResponse:
        logger.info(f"Generating patient audio briefing summary narration for claim {state.claim_id}")

        # 1. Resolve Patient Name
        patient_name = "Patient"
        if state.financial_report and state.financial_report.patient_name:
            patient_name = state.financial_report.patient_name
        elif state.cob_decision and state.cob_decision.patient_name:
            patient_name = state.cob_decision.patient_name
        elif state.member_id == "98765":
            patient_name = "Priya Sen"
        elif state.member_id == "54321":
            patient_name = "Aarav Sen"

        first_name = patient_name.split()[0] if patient_name else "there"

        # 2. Section: Greeting
        greeting_text = f"Hello {first_name}."

        # 3. Section: Summary
        doc_names = []
        if state.processed_documents:
            for doc_type in state.processed_documents.keys():
                if doc_type == DocumentType.PRIYA_PT_INVOICE:
                    doc_names.append("your physical therapy invoice")
                elif doc_type == DocumentType.AARAV_MRI_REPORT:
                    doc_names.append("your knee MRI report")
                elif doc_type == DocumentType.SURGEON_ESTIMATE:
                    doc_names.append("your surgeon fee estimate sheet")
                elif doc_type == DocumentType.USER_QUERY_TRANSCRIPT:
                    doc_names.append("your benefit query transcript")
        
        if not doc_names:
            doc_names = ["your uploaded medical documents"]

        if len(doc_names) > 1:
            docs_joined = ", and ".join([", ".join(doc_names[:-1]), doc_names[-1]])
        else:
            docs_joined = doc_names[0]

        findings_narrative = "which outline the medical services and treatments received for your knee care."
        if state.coding_result and state.coding_result.diagnoses:
            primary_diag = state.coding_result.diagnoses[0].description.lower()
            findings_narrative = f"which confirm the clinical diagnosis of {primary_diag}."

        summary_text = (
            f"We have completed the analysis of {docs_joined}, {findings_narrative} "
            "Our automated team has processed these files to coordinate your benefits."
        )

        # 4. Section: Insurance
        primary_insurer = "your primary plan"
        secondary_insurer = "your secondary plan"
        if state.primary_policy:
            primary_insurer = state.primary_policy.provider_name
        if state.secondary_policy:
            secondary_insurer = state.secondary_policy.provider_name

        if state.primary_policy and state.secondary_policy:
            insurance_text = (
                f"We identified {primary_insurer} as your primary insurance provider, "
                f"and {secondary_insurer} as your secondary insurance provider. "
                "Both plans were coordinated to maximize your coverage and reduce your final bill."
            )
        elif state.primary_policy:
            insurance_text = (
                f"We resolved your active insurance policy with {primary_insurer}. "
                "This policy will be billed as the primary payer for your medical services."
            )
        else:
            insurance_text = "We did not find any active insurance policy details registered for your claim."

        # 5. Section: Financial Summary
        total_billed = 0.0
        primary_paid = 0.0
        secondary_paid = 0.0
        patient_responsibility = 0.0

        if state.financial_report and state.financial_report.breakdown and state.financial_report.breakdown.summary:
            total_billed = state.financial_report.breakdown.summary.total_billed
            primary_paid = state.financial_report.breakdown.summary.total_primary_paid
            secondary_paid = state.financial_report.breakdown.summary.total_secondary_paid
            patient_responsibility = state.financial_report.breakdown.summary.total_patient_responsibility
        elif state.cob_decision:
            total_billed = state.cob_decision.total_billed
            primary_paid = state.cob_decision.total_primary_paid
            secondary_paid = state.cob_decision.total_secondary_paid
            patient_responsibility = state.cob_decision.total_patient_responsibility

        financial_text = (
            f"The total billed amount from your provider is {total_billed:.2f} dollars. "
            f"Your primary insurance is expected to cover {primary_paid:.2f} dollars, "
        )
        if secondary_paid > 0:
            financial_text += f"and your secondary insurance is expected to coordinate an additional payment of {secondary_paid:.2f} dollars. "
        
        financial_text += f"This leaves you with an estimated personal responsibility of {patient_responsibility:.2f} dollars."

        # 6. Section: Pre-Authorization
        preauth_required_insurers = []
        if state.coding_result and state.coding_result.procedures:
            # Check primary rules
            if state.primary_policy:
                for proc in state.coding_result.procedures:
                    for rule in state.primary_policy.coverage_rules:
                        if rule.cpt_code == proc.code and rule.requires_preauth:
                            preauth_required_insurers.append(state.primary_policy.provider_name)
                            break
            # Check secondary rules
            if state.secondary_policy:
                for proc in state.coding_result.procedures:
                    for rule in state.secondary_policy.coverage_rules:
                        if rule.cpt_code == proc.code and rule.requires_preauth:
                            preauth_required_insurers.append(state.secondary_policy.provider_name)
                            break

        # Deduplicate list
        preauth_required_insurers = list(set(preauth_required_insurers))

        if preauth_required_insurers:
            insurers_str = " and ".join(preauth_required_insurers)
            preauth_text = (
                f"Please note that prior authorization is required by {insurers_str} "
                "for your scheduled procedures. Our administrative team has already generated "
                "the necessary prior-authorization request letters, which are ready for submission."
            )
        else:
            preauth_text = (
                "Good news: prior authorization is not required for these services under your active plans. "
                "This means your treatment can proceed immediately without waiting for insurance approval."
            )

        # 7. Section: Closing
        if preauth_required_insurers:
            closing_text = (
                "We will submit the prior-authorization letters to your insurers today. "
                "We recommend contacting our clinic scheduler in five to seven business days "
                "to check the status of your authorization and book your treatment."
            )
        else:
            closing_text = (
                "No further action is required from you. We will file the claim directly with your insurers. "
                "We recommend keeping copies of your billing statements for your personal records once they arrive."
            )

        # Compile sections
        sections = [
            AudioSection(title="Greeting", text=greeting_text),
            AudioSection(title="Summary", text=summary_text),
            AudioSection(title="Insurance", text=insurance_text),
            AudioSection(title="Financial Summary", text=financial_text),
            AudioSection(title="Pre-Authorization", text=preauth_text),
            AudioSection(title="Closing", text=closing_text),
        ]

        full_narration = " ".join([sec.text for sec in sections])
        
        # Estimate duration: average speaking rate of 140 WPM (2.33 words per second)
        word_count = len(full_narration.split())
        estimated_duration_seconds = round((word_count / 140.0) * 60.0, 1)

        briefing = AudioBriefing(
            patient_name=patient_name,
            sections=sections,
            full_narration=full_narration,
            estimated_duration_seconds=estimated_duration_seconds,
        )

        return AudioResponse(
            claim_id=state.claim_id,
            briefing=briefing,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )

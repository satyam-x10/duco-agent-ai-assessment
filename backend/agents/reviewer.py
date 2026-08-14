import os
import json
import logging
from typing import List
from google import genai
from pydantic import BaseModel
from app.core.adk import Agent, SharedWorkflowState

logger = logging.getLogger(__name__)


class GeminiReviewResponse(BaseModel):
    warnings: List[str]
    requires_human_approval: bool
    rationale: str


class ReviewerAgent(Agent):
    """Specialist agent responsible for validating pipeline outputs, structural completeness, and quality warning checks."""

    def __init__(self):
        super().__init__("ReviewerAgent")

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} auditing workflow outputs for claim {state.claim_id}")
        
        if state.mock_mode:
            import asyncio
            await asyncio.sleep(0.8)
            
        # Preserve grounding/document warnings produced by deterministic tools;
        # clear only prior reviewer findings before a fresh audit.
        state.warnings = [
            warning for warning in state.warnings
            if warning.startswith("[Grounding Inconsistency]")
            or warning.startswith("[Document Quality]")
        ]

        # 1. Run deterministic Python checks (which populate state.warnings and throw ValueErrors if structure is broken)
        self._run_python_checks(state)

        # 2. Run Gemini clinical report audit if not in mock mode and API key is present
        if not state.mock_mode:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                try:
                    # Build combined text from parsed documents
                    combined_text_parts = []
                    for doc_type, doc in state.processed_documents.items():
                        combined_text_parts.append(f"--- DOCUMENT TYPE: {doc_type.value} ---\n{doc.extracted_text}\n")
                    combined_text = "\n".join(combined_text_parts)

                    # Extract codes info
                    diagnoses_str = ", ".join([f"{d.code} ({d.description})" for d in state.coding_result.diagnoses]) if state.coding_result else "None"
                    procedures_str = ", ".join([f"{p.code} ({p.description})" for p in state.coding_result.procedures]) if state.coding_result else "None"

                    # Primary / Secondary policy details
                    primary_policy_info = f"ID: {state.primary_policy.policy_id}, Provider: {state.primary_policy.provider_name}, Members: " + ", ".join([f"{m.first_name} {m.last_name} ({m.role})" for m in state.primary_policy.members]) if state.primary_policy else "None"
                    secondary_policy_info = f"ID: {state.secondary_policy.policy_id}, Provider: {state.secondary_policy.provider_name}, Members: " + ", ".join([f"{m.first_name} {m.last_name} ({m.role})" for m in state.secondary_policy.members]) if state.secondary_policy else "None"

                    prompt = f"""
You are an expert medical claims auditor and logical consistency agent.
Your task is to analyze the extracted document texts, resolved insurance policies, and extracted medical codes (procedures and diagnoses) to decide if the claim is logically consistent, medically necessary, and should go forward/be approved, or if it has discrepancies that require manual clinician review and backtracking.

Clinical Documents (Extracted Text):
\"\"\"
{combined_text}
\"\"\"

Extracted Medical Codes:
- Diagnoses: {diagnoses_str}
- Procedures: {procedures_str}

Insurance Policies:
- Primary Policy: {primary_policy_info}
- Secondary Policy: {secondary_policy_info}

Please check for and perform these specific validations:
1. Patient name discrepancies: Validate if the patient names in the clinical documents match the insured members on the active policies.
   - If a name is missing or mismatched between clinical files and the policy member ID associated with this claim, log a warning prefixing it with `[Policy Inconsistency]`.
2. Policy name mismatches: Check if the patient name is consistent across primary and secondary policies. If mismatched, log a warning prefixing it with `[Policy Inconsistency]`.
3. Medical necessity and clinical consistency: Validate if the extracted procedures are medically necessary and fully supported by the findings in the clinical documents.
   - Crucially: If a procedure (like ACL reconstruction 29888 or Meniscectomy 29881) is listed, but the diagnostic MRI report states that structure is normal, intact, or has no tear (e.g. "no ACL tear"), then the procedure is NOT medically necessary. If a procedure lacks supporting injury diagnosis or clinical justification in the text, log a warning prefixing it with `[Coding Inconsistency]`.
4. Code confidence: Check if any diagnosis/procedure codes were extracted with low confidence (e.g. < 0.70). If so, log a warning: "Low confidence ...".

If you find policy/name discrepancies or medical coding inconsistencies/lack of medical necessity, set requires_human_approval to true. Provide a detailed audit rationale in your response.
"""

                    client = genai.Client(api_key=api_key)
                    logger.info("Calling Gemini API to review/audit claim logical consistency.")
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": GeminiReviewResponse,
                        },
                    )

                    parsed_data = json.loads(response.text)
                    validated = GeminiReviewResponse(**parsed_data)

                    state.warnings.extend(validated.warnings)
                    if validated.requires_human_approval:
                        state.requires_human_approval = True
                    logger.info(f"Gemini Audit Rationale: {validated.rationale}")
                    logger.info(f"Gemini Audit complete. Generated {len(validated.warnings)} warnings. Requires human approval: {state.requires_human_approval}")

                except Exception as e:
                    logger.error(f"Gemini clinical audit failed: {e}", exc_info=True)
                    # Proceed with existing warnings

        # Check if manual human approval is required due to low confidence warnings or inconsistencies
        if any("Low confidence" in w or "Inconsistency" in w for w in state.warnings):
            state.requires_human_approval = True
            logger.info(f"{self.name} flagged workflow as requiring manual clinician audit approval.")
            
        logger.info(f"{self.name} completed validation audit. Generated {len(state.warnings)} warning indicators.")

    def _run_python_checks(self, state: SharedWorkflowState) -> None:
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

        for document_type, document in state.processed_documents.items():
            if document.confidence < 0.90 or document.quality_issues:
                details = "; ".join(document.quality_issues) or f"confidence {document.confidence:.2f}"
                state.warnings.append(f"[Document Quality] {document_type.value}: {details}")
                state.requires_human_approval = True
            
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
            else:
                # Check for specific procedure-diagnosis mismatches (medical necessity)
                has_acl_reconstruction = any(p.code == "29888" for p in procedures)
                has_acl_tear = any(d.code.startswith("S83.51") for d in diagnoses)
                if has_acl_reconstruction and not has_acl_tear:
                    state.warnings.append("[Coding Inconsistency] Extracted procedure 29888 (ACL Reconstruction) lacks a supporting ACL injury diagnosis code (S83.51) in the coding result.")

                has_meniscectomy = any(p.code == "29881" for p in procedures)
                has_meniscus_tear = any(d.code.startswith("M23.2") or d.code.startswith("S83.2") for d in diagnoses)
                if has_meniscectomy and not has_meniscus_tear:
                    state.warnings.append("[Coding Inconsistency] Extracted procedure 29881 (Arthroscopic Meniscectomy) lacks a supporting meniscus tear diagnosis code in the coding result.")

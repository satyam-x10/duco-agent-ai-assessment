import logging
from datetime import datetime
from string import Template
from typing import List, Optional

from app.schemas.cob_engine import COBDecision
from app.schemas.preauth import PreAuthLetter, PreAuthResponse
from app.core.adk import SharedWorkflowState

logger = logging.getLogger(__name__)

LETTER_TEMPLATE = """# PRIOR AUTHORIZATION REQUEST
**DATE:** ${date_generated}
**TO:** Prior Authorization Department, ${insurer_name}
**FAX / PORTAL SECURE SUBMISSION**

---

### 1. PATIENT & POLICY INFORMATION
*   **Patient Name:** ${patient_name}
*   **Date of Birth:** ${patient_dob}
*   **Member ID:** ${member_id}
*   **Policy ID / Plan:** ${policy_id}
*   **Group Number:** ${group_number}

### 2. PROVIDER / CLINICAL SITE INFORMATION
*   **Requesting Provider:** Dr. Sarah Jenkins, MD
*   **Provider NPI:** 1982736450
*   **Facility Name:** Summit Healthcare Clinic
*   **Facility Address:** 1200 Medical Center Pkwy, Suite 400, Summit, NJ 07901
*   **Contact Phone:** (555) 0199-2831
*   **Contact Fax:** (555) 0199-2832

### 3. DIAGNOSIS (ICD-10-CM CODES)
${diagnoses_list}

### 4. REQUESTED PROCEDURES & ESTIMATED COST BREAKDOWN
The following procedures are requested for prior authorization review under this policy:

| CPT Code | Procedure Description | Estimated Billed | Requires Pre-Auth? |
| :--- | :--- | :--- | :--- |
${procedures_rows}

*   **Total Estimated Billed Charges:** ₹${total_billed}

### 5. CLINICAL STATEMENT & MEDICAL NECESSITY
*   **Primary Clinical Indications:** ${clinical_findings}
*   **Medical Necessity Summary:** The requested services/procedures listed above are indicated as medically necessary for the management of the patient's diagnosed condition (${primary_diagnosis_code} - ${primary_diagnosis_desc}). Failure to authorize these services may lead to progressive functional decline, joint instability, or chronic pain conditions. Physical therapist or surgeon evaluations confirm that conservative treatments have been evaluated, and the requested interventions represent the current standard of clinical care.

---
**Prepared By:** Summit Healthcare Prior Authorization Team
**NPI / Representative Signature:** *Dr. Sarah Jenkins, MD*
"""


class PreAuthorizationService:
    """Service responsible for generating professional pre-authorization request letters from claims details."""

    def generate_letters(self, state: SharedWorkflowState) -> PreAuthResponse:
        # Check if any procedure requires pre-authorization
        any_requires_preauth = False
        procedures = state.coding_result.procedures if state.coding_result else []
        
        # Helper to determine if a procedure is medically necessary based on cob_decision
        def is_medically_necessary(cpt: str) -> bool:
            if state.cob_decision and state.cob_decision.lines_coverage:
                for line in state.cob_decision.lines_coverage:
                    if line.cpt_code == cpt:
                        notes = line.remaining_balance.notes or ""
                        if "not medically necessary" in notes.lower():
                            return False
            return True

        policies = []
        if state.primary_policy:
            policies.append(state.primary_policy)
        if state.secondary_policy:
            policies.append(state.secondary_policy)
            
        from services.rules_database import rules_db

        for policy in policies:
            for proc in procedures:
                if not is_medically_necessary(proc.code):
                    continue
                # Query both policy rules and external RulesDatabaseService
                if rules_db.is_preauth_required(proc.code):
                    any_requires_preauth = True
                    break
                for rule in policy.coverage_rules:
                    if rule.cpt_code == proc.code and rule.requires_preauth:
                        any_requires_preauth = True
                        break
                if any_requires_preauth:
                    break
            if any_requires_preauth:
                break
                
        if not any_requires_preauth:
            logger.info("No procedure requires pre-authorization or is medically necessary. Skipping letter generation.")
            return PreAuthResponse(claim_id=state.claim_id, letters=[])

        logger.info(f"Generating pre-authorization letters for claim {state.claim_id}")

        patient_name = "Priya Sen"
        if state.financial_report and state.financial_report.patient_name:
            patient_name = state.financial_report.patient_name
        elif state.cob_decision and state.cob_decision.patient_name:
            patient_name = state.cob_decision.patient_name

        letters: List[PreAuthLetter] = []
        policies = []
        if state.primary_policy:
            policies.append(state.primary_policy)
        if state.secondary_policy:
            policies.append(state.secondary_policy)

        date_generated = datetime.utcnow().strftime("%B %d, %Y")
        timestamp_iso = datetime.utcnow().isoformat() + "Z"

        # Build Diagnosis list
        diagnoses_list = "*No active diagnosis codes resolved.*"
        primary_diag_code = "N/A"
        primary_diag_desc = "N/A"
        
        diagnoses = state.coding_result.diagnoses if state.coding_result else []
        procedures = state.coding_result.procedures if state.coding_result else []

        if diagnoses:
            diagnoses_list = "\n".join([f"*   **{d.code}:** {d.description}" for d in diagnoses])
            primary_diag_code = diagnoses[0].code
            primary_diag_desc = diagnoses[0].description

        # Determine clinical findings narrative
        clinical_findings = "The patient presents with clinical indications including joint pain, restricted range of motion, and functional impairment. Physical evaluations support the requested course of treatment."
        if any(d.code.startswith("M23") for d in diagnoses):
            clinical_findings = "MRI lower extremity joint demonstrates a tear of the medial meniscus, joint effusion, and structural ligament laxity. Conservative therapy failure is documented."

        for policy in policies:
            # Resolve patient details on this policy
            patient_member = next(
                (m for m in policy.members if 
                 m.first_name.lower() in patient_name.lower() or 
                 patient_name.lower() in m.first_name.lower()), 
                None
            )
            patient_dob = patient_member.date_of_birth if patient_member else "N/A"
            member_id = patient_member.member_id if patient_member else "N/A"

            # Render procedure table rows
            procedures_rows = []
            total_billed = 0.0

            # CPT Billed lookup map (mirroring the COB Engine estimate values in INR)
            cpt_billed_map = {
                "97161": 20000.00,
                "97110": 10000.00,
                "73721": 12000.00,
                "29881": 100000.00,
                "29888": 350000.00
            }

            for proc in procedures:
                if not is_medically_necessary(proc.code):
                    continue
                cost = cpt_billed_map.get(proc.code, 500.00)
                if state.cob_decision:
                    for line in state.cob_decision.lines_coverage:
                        if line.cpt_code == proc.code:
                            cost = line.billed_amount
                            break
                total_billed += cost

                # Determine if pre-auth is required under this specific policy
                requires_preauth = False
                for rule in policy.coverage_rules:
                    if rule.cpt_code == proc.code:
                        requires_preauth = rule.requires_preauth
                        break

                preauth_str = "YES (Required)" if requires_preauth else "No (Covered)"
                procedures_rows.append(f"| `{proc.code}` | {proc.description} | ₹{cost:,.2f} | {preauth_str} |")

            procedures_table = "\n".join(procedures_rows) if procedures_rows else "| N/A | No procedures requested | ₹0.00 | - |"

            # Render the Template
            template = Template(LETTER_TEMPLATE)
            letter_content = template.substitute(
                date_generated=date_generated,
                insurer_name=policy.provider_name,
                patient_name=patient_name,
                patient_dob=patient_dob,
                member_id=member_id,
                policy_id=policy.policy_id,
                group_number=policy.group_number,
                diagnoses_list=diagnoses_list,
                procedures_rows=procedures_table,
                total_billed=f"{total_billed:,.2f}",
                clinical_findings=clinical_findings,
                primary_diagnosis_code=primary_diag_code,
                primary_diagnosis_desc=primary_diag_desc,
            )

            letters.append(
                PreAuthLetter(
                    insurer_name=policy.provider_name,
                    policy_id=policy.policy_id,
                    patient_name=patient_name,
                    letter_content=letter_content,
                    generated_at=timestamp_iso,
                )
            )

        return PreAuthResponse(
            claim_id=state.claim_id,
            letters=letters
        )

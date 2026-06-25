import logging
from typing import List, Optional, Tuple

from app.schemas.insurance_engine import InsurancePolicy, Member
from app.schemas.cob_engine import (
    Claim,
    ClaimLine,
    PrimaryCoverage,
    SecondaryCoverage,
    RemainingBalance,
    ClaimLineCoverage,
    COBDecision,
)
from services.insurance_engine import InsuranceService

logger = logging.getLogger(__name__)


class COBEngine:
    """Engine responsible for resolving payment order and coordinating benefits for dual-coverage claims."""

    def __init__(self, insurance_service: InsuranceService):
        self.insurance_service = insurance_service

    def determine_payment_order(
        self, patient_member: Member, policies: List[InsurancePolicy]
    ) -> Tuple[Optional[InsurancePolicy], Optional[InsurancePolicy]]:
        """Resolves primary vs. secondary insurance policies using standard COB rules.

        Rules applied:
        1. Subscriber vs. Dependent (Subscriber is primary)
        2. Birthday Rule for dependents covered on both parents' plans (Earliest birth month/day is primary)
        3. Stable sorting fallback (alphabetical by policy ID) if rules yield a tie.
        """
        if not policies:
            return None, None
        if len(policies) == 1:
            return policies[0], None

        # Build policy-to-member mapping for the patient
        policy_members: List[Tuple[InsurancePolicy, Member]] = []
        for policy in policies:
            for member in policy.members:
                if (
                    member.first_name.lower() == patient_member.first_name.lower()
                    and member.last_name.lower() == patient_member.last_name.lower()
                    and member.date_of_birth == patient_member.date_of_birth
                ):
                    policy_members.append((policy, member))
                    break

        # If we couldn't match the member in both policies, fallback
        if len(policy_members) < 2:
            resolved_policies = [pm[0] for pm in policy_members]
            other_policies = [p for p in policies if p not in resolved_policies]
            all_resolved = resolved_policies + other_policies
            return all_resolved[0], all_resolved[1] if len(all_resolved) > 1 else None

        # Evaluate Subscriber vs Dependent
        sub_policies = [pm for pm in policy_members if pm[1].role == "subscriber"]
        dep_policies = [pm for pm in policy_members if pm[1].role == "dependent"]

        if len(sub_policies) == 1 and len(dep_policies) == 1:
            logger.info(f"COB resolved: Subscriber policy primary ({sub_policies[0][0].policy_id}) vs Dependent secondary ({dep_policies[0][0].policy_id})")
            return sub_policies[0][0], dep_policies[0][0]

        # Evaluate Birthday Rule (if dependent on both)
        if len(dep_policies) == 2:
            birthdays: List[Tuple[InsurancePolicy, Tuple[int, int]]] = []
            for policy, member in dep_policies:
                # Find subscriber DOB on this policy
                subscriber = next((m for m in policy.members if m.role == "subscriber"), None)
                if subscriber:
                    try:
                        # Parse birth month and day (e.g. 1985-04-12 -> month 4, day 12)
                        parts = subscriber.date_of_birth.split("-")
                        month = int(parts[1])
                        day = int(parts[2])
                        birthdays.append((policy, (month, day)))
                    except Exception as e:
                        logger.error(f"Error parsing subscriber DOB {subscriber.date_of_birth} on policy {policy.policy_id}: {e}")
                else:
                    # Default if no subscriber found
                    birthdays.append((policy, (12, 31)))

            # Compare parent birthdays
            if len(birthdays) == 2:
                p1, b1 = birthdays[0]
                p2, b2 = birthdays[1]
                if b1 < b2:
                    logger.info(f"COB Birthday Rule: Parent birthday {b1} earlier than {b2}. Primary: {p1.policy_id}")
                    return p1, p2
                elif b2 < b1:
                    logger.info(f"COB Birthday Rule: Parent birthday {b2} earlier than {b1}. Primary: {p2.policy_id}")
                    return p2, p1

        # Tie-breaker fallback: alphabetically by policy ID
        sorted_pm = sorted(policy_members, key=lambda x: x[0].policy_id)
        logger.info(f"COB Tie-breaker: Fallback to alphabetical policy ID. Primary: {sorted_pm[0][0].policy_id}")
        return sorted_pm[0][0], sorted_pm[1][0]

    def coordinate_benefits(self, claim: Claim) -> COBDecision:
        """Adjudicates a claim, resolving payment order and coordinating benefits across plans."""
        # 1. Look up patient member
        patient_member = self.insurance_service.get_member(claim.member_id)
        if not patient_member:
            raise ValueError(f"Patient member with ID '{claim.member_id}' not found.")

        # 2. Find all policies covering this member
        matched_policies: List[InsurancePolicy] = []
        for policy in self.insurance_service._policies.values():
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

        # 3. Determine primary vs secondary
        primary_policy, secondary_policy = self.determine_payment_order(patient_member, matched_policies)

        # 4. Resolve member IDs under primary and secondary plans (since they might differ)
        primary_member_id = claim.member_id
        secondary_member_id = ""

        if primary_policy:
            primary_mem = next(
                (m for m in primary_policy.members if 
                 m.first_name.lower() == patient_member.first_name.lower() and 
                 m.last_name.lower() == patient_member.last_name.lower()), 
                None
            )
            if primary_mem:
                primary_member_id = primary_mem.member_id

        if secondary_policy:
            secondary_mem = next(
                (m for m in secondary_policy.members if 
                 m.first_name.lower() == patient_member.first_name.lower() and 
                 m.last_name.lower() == patient_member.last_name.lower()), 
                None
            )
            if secondary_mem:
                secondary_member_id = secondary_mem.member_id

        # 5. Adjudicate claim lines
        lines_coverage: List[ClaimLineCoverage] = []
        total_billed = 0.0
        total_primary_paid = 0.0
        total_secondary_paid = 0.0
        total_patient_responsibility = 0.0

        for line in claim.lines:
            billed = line.billed_amount
            total_billed += billed

            # A. Primary Adjudication
            is_pri_covered = False
            pri_ded_applied = 0.0
            pri_coins_rate = 0.0
            pri_coins_amt = 0.0
            pri_paid = 0.0
            pri_patient_resp = billed

            if primary_policy:
                # Find matching coverage rule
                is_pri_covered = self.insurance_service.is_procedure_covered(primary_member_id, line.cpt_code)
                if is_pri_covered:
                    # Apply primary individual deductible
                    rem_individual = primary_policy.deductible.remaining_individual
                    pri_ded_applied = min(billed, rem_individual)
                    
                    # Update primary individual and family deductibles in-memory
                    primary_policy.deductible.remaining_individual = max(0.0, rem_individual - pri_ded_applied)
                    primary_policy.deductible.remaining_family = max(0.0, primary_policy.deductible.remaining_family - pri_ded_applied)
                    
                    # Calculate Coinsurance
                    subject_to_coins = billed - pri_ded_applied
                    pri_coins_rate = primary_policy.coinsurance.rate
                    pri_coins_amt = subject_to_coins * pri_coins_rate
                    pri_paid = subject_to_coins * (1.0 - pri_coins_rate)
                    pri_patient_resp = pri_ded_applied + pri_coins_amt

            primary_coverage = PrimaryCoverage(
                policy_id=primary_policy.policy_id if primary_policy else "",
                is_covered=is_pri_covered,
                deductible_applied=pri_ded_applied,
                coinsurance_rate=pri_coins_rate,
                coinsurance_amount=pri_coins_amt,
                primary_paid=pri_paid,
                patient_responsibility=pri_patient_resp,
            )

            # B. Secondary Adjudication (Coordination of Benefits)
            is_sec_covered = False
            sec_ded_applied = 0.0
            sec_coins_rate = 0.0
            sec_coins_amt = 0.0
            sec_paid = 0.0
            sec_patient_resp = pri_patient_resp

            notes_msg = ""

            if secondary_policy and is_pri_covered:
                # Check if CPT code is covered under secondary policy
                is_sec_covered = self.insurance_service.is_procedure_covered(secondary_member_id, line.cpt_code)
                if is_sec_covered:
                    # Calculate secondary normal benefit (what secondary would pay if it were primary)
                    sec_rem_ded = secondary_policy.deductible.remaining_individual
                    sec_ded_applied_if_primary = min(billed, sec_rem_ded)
                    sec_coins_rate = secondary_policy.coinsurance.rate
                    
                    sec_normal_paid = (billed - sec_ded_applied_if_primary) * (1.0 - sec_coins_rate)
                    
                    # Secondary pays the lesser of:
                    # 1. Patient responsibility after primary
                    # 2. What secondary would pay if primary
                    sec_paid = min(pri_patient_resp, sec_normal_paid)
                    
                    # Determine secondary deductible satisfied.
                    # Patient actual expenses credited to secondary deductible
                    sec_ded_satisfied = min(pri_patient_resp, sec_ded_applied_if_primary)
                    secondary_policy.deductible.remaining_individual = max(0.0, sec_rem_ded - sec_ded_satisfied)
                    secondary_policy.deductible.remaining_family = max(0.0, secondary_policy.deductible.remaining_family - sec_ded_satisfied)
                    
                    sec_ded_applied = sec_ded_satisfied
                    sec_coins_amt = max(0.0, pri_patient_resp - sec_paid - sec_ded_applied)
                    sec_patient_resp = pri_patient_resp - sec_paid
                    
                    notes_msg = (
                        f"Primary paid {pri_paid:.2f} (Deductible: {pri_ded_applied:.2f}, Coinsurance: {pri_coins_amt:.2f}). "
                        f"Secondary coordinated and paid {sec_paid:.2f} (deductible credited: {sec_ded_applied:.2f})."
                    )
                else:
                    notes_msg = f"Procedure not covered under secondary policy {secondary_policy.policy_id}."
            elif secondary_policy and not is_pri_covered:
                # Primary excluded this procedure. Check if secondary covers it.
                is_sec_covered = self.insurance_service.is_procedure_covered(secondary_member_id, line.cpt_code)
                if is_sec_covered:
                    # Secondary behaves as primary since primary didn't cover
                    sec_rem_ded = secondary_policy.deductible.remaining_individual
                    sec_ded_applied = min(billed, sec_rem_ded)
                    
                    secondary_policy.deductible.remaining_individual = max(0.0, sec_rem_ded - sec_ded_applied)
                    secondary_policy.deductible.remaining_family = max(0.0, secondary_policy.deductible.remaining_family - sec_ded_applied)
                    
                    sec_coins_rate = secondary_policy.coinsurance.rate
                    subject_to_coins = billed - sec_ded_applied
                    sec_coins_amt = subject_to_coins * sec_coins_rate
                    sec_paid = subject_to_coins * (1.0 - sec_coins_rate)
                    sec_patient_resp = sec_ded_applied + sec_coins_amt
                    
                    notes_msg = f"Procedure excluded by primary. Secondary processed as primary, paying {sec_paid:.2f}."
                else:
                    notes_msg = "Procedure excluded by both primary and secondary policies."
            else:
                notes_msg = f"Single coverage only. Billed patient remaining: {pri_patient_resp:.2f}."

            secondary_coverage = SecondaryCoverage(
                policy_id=secondary_policy.policy_id if secondary_policy else "",
                is_covered=is_sec_covered,
                deductible_applied=sec_ded_applied,
                coinsurance_rate=sec_coins_rate,
                coinsurance_amount=sec_coins_amt,
                secondary_paid=sec_paid,
                patient_responsibility=sec_patient_resp,
            )

            # C. Final Remaining Balance
            remaining_balance = RemainingBalance(
                billed_amount=billed,
                primary_paid=pri_paid,
                secondary_paid=sec_paid,
                patient_responsibility=sec_patient_resp,
                notes=notes_msg,
            )

            total_primary_paid += pri_paid
            total_secondary_paid += sec_paid
            total_patient_responsibility += sec_patient_resp

            lines_coverage.append(
                ClaimLineCoverage(
                    cpt_code=line.cpt_code,
                    billed_amount=billed,
                    primary_coverage=primary_coverage,
                    secondary_coverage=secondary_coverage,
                    remaining_balance=remaining_balance,
                )
            )

        return COBDecision(
            claim_id=claim.claim_id,
            patient_name=f"{patient_member.first_name} {patient_member.last_name}",
            primary_policy_id=primary_policy.policy_id if primary_policy else None,
            primary_provider=primary_policy.provider_name if primary_policy else None,
            secondary_policy_id=secondary_policy.policy_id if secondary_policy else None,
            secondary_provider=secondary_policy.provider_name if secondary_policy else None,
            lines_coverage=lines_coverage,
            total_billed=total_billed,
            total_primary_paid=total_primary_paid,
            total_secondary_paid=total_secondary_paid,
            total_patient_responsibility=total_patient_responsibility,
        )

import logging
from decimal import Decimal, ROUND_HALF_UP
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
from services.clinical_rules import ClinicalRulesService

logger = logging.getLogger(__name__)

PENCE = Decimal("0.01")


def _d(value: float | int | str | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(PENCE, rounding=ROUND_HALF_UP)
    try:
        return Decimal(str(value)).quantize(PENCE, rounding=ROUND_HALF_UP)
    except Exception:
        try:
            return Decimal(float(value)).quantize(PENCE, rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal("0.00")


def _f(d: Decimal) -> float:
    return float(d.quantize(PENCE, rounding=ROUND_HALF_UP))


class COBEngine:
    """Engine responsible for resolving payment order and coordinating benefits for dual-coverage claims."""

    def __init__(self, insurance_service: InsuranceService, clinical_rules_service: Optional[ClinicalRulesService] = None):
        self.insurance_service = insurance_service
        self.clinical_rules_service = clinical_rules_service or ClinicalRulesService()

    def check_medical_necessity(self, cpt_code: str, diagnosis_codes: List[str]) -> Tuple[bool, str]:
        """Checks if a CPT procedure is medically necessary based on clinical rule catalog."""
        if not diagnosis_codes:
            return True, ""
        supports, rationale = self.clinical_rules_service.supports(cpt_code, diagnosis_codes)
        if supports is False:
            return False, rationale
        return True, ""

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

        if len(policy_members) < 2:
            resolved_policies = [pm[0] for pm in policy_members]
            other_policies = [p for p in policies if p not in resolved_policies]
            all_resolved = resolved_policies + other_policies
            if not all_resolved:
                return (policies[0] if policies else None), (policies[1] if len(policies) > 1 else None)
            return all_resolved[0], all_resolved[1] if len(all_resolved) > 1 else None

        # Evaluate Subscriber vs Dependent
        sub_policies = [pm for pm in policy_members if pm[1].role == "subscriber"]
        dep_policies = [pm for pm in policy_members if pm[1].role == "dependent"]

        if len(sub_policies) == 1 and len(dep_policies) == 1:
            logger.info(f"COB resolved: Subscriber primary ({sub_policies[0][0].policy_id}) vs Dependent secondary ({dep_policies[0][0].policy_id})")
            return sub_policies[0][0], dep_policies[0][0]

        # Evaluate Birthday Rule (if dependent on both)
        if len(dep_policies) >= 2:
            birthdays: List[Tuple[InsurancePolicy, Tuple[int, int]]] = []
            for policy, member in dep_policies:
                subscriber = next((m for m in policy.members if m.role == "subscriber"), None)
                if subscriber:
                    try:
                        parts = subscriber.date_of_birth.split("-")
                        month = int(parts[1])
                        day = int(parts[2])
                        birthdays.append((policy, (month, day)))
                    except Exception as e:
                        logger.error(f"Error parsing subscriber DOB on policy {policy.policy_id}: {e}")
                        birthdays.append((policy, (12, 31)))
                else:
                    birthdays.append((policy, (12, 31)))

            if len(birthdays) == 2:
                p1, b1 = birthdays[0]
                p2, b2 = birthdays[1]
                if b1 < b2:
                    return p1, p2
                elif b2 < b1:
                    return p2, p1

        # Fallback to alphabetical policy ID
        sorted_pm = sorted(policy_members, key=lambda x: x[0].policy_id)
        return sorted_pm[0][0], sorted_pm[1][0]

    def coordinate_benefits(self, claim: Claim) -> COBDecision:
        """Adjudicates a claim with isolated per-claim state, Decimal arithmetic, and conservation checks."""
        patient_member = self.insurance_service.get_member(claim.member_id)
        if not patient_member:
            raise ValueError(f"Patient member with ID '{claim.member_id}' not found.")

        # Obtain deep-copied policies isolated from global state
        matched_policies = []
        if hasattr(self.insurance_service, "get_policies_for_member") and callable(getattr(self.insurance_service, "get_policies_for_member")):
            try:
                res = self.insurance_service.get_policies_for_member(patient_member)
                if isinstance(res, list) and all(isinstance(p, InsurancePolicy) for p in res):
                    matched_policies = res
            except Exception:
                matched_policies = []

        if not matched_policies:
            policies_dict = getattr(self.insurance_service, "_policies", {})
            if isinstance(policies_dict, dict):
                for p in policies_dict.values():
                    if hasattr(p, "members") and any(
                        getattr(m, "member_id", None) == claim.member_id
                        or (
                            getattr(m, "first_name", "").lower() == getattr(patient_member, "first_name", "").lower()
                            and getattr(m, "last_name", "").lower() == getattr(patient_member, "last_name", "").lower()
                        )
                        for m in getattr(p, "members", [])
                    ):
                        matched_policies.append(p.model_copy(deep=True) if hasattr(p, "model_copy") else p)

        if not matched_policies:
            raise ValueError(f"No insurance policies found covering patient {patient_member.first_name} {patient_member.last_name}.")

        primary_policy, secondary_policy = self.determine_payment_order(patient_member, matched_policies)

        # Track per-claim ledger balances using Decimal
        rem_indiv_ded: dict[str, Decimal] = {}
        rem_fam_ded: dict[str, Decimal] = {}
        rem_indiv_oop: dict[str, Decimal] = {}

        for p in matched_policies:
            rem_fam_ded[p.policy_id] = _d(p.deductible.remaining_family)
            for m in p.members:
                key = f"{p.policy_id}:{m.member_id}"
                rem_indiv_ded[key] = _d(p.deductible.remaining_individual)
                rem_indiv_oop[key] = _d(p.remaining_out_of_pocket_max)

        lines_coverage: List[ClaimLineCoverage] = []
        tot_billed = Decimal("0.00")
        tot_primary_paid = Decimal("0.00")
        tot_secondary_paid = Decimal("0.00")
        tot_patient_resp = Decimal("0.00")

        patient_name = f"{patient_member.first_name} {patient_member.last_name}"

        # Resolve primary and secondary member identifiers
        primary_mem_id = claim.member_id
        secondary_mem_id = ""
        if primary_policy:
            pm = next((m for m in primary_policy.members if m.first_name.lower() == patient_member.first_name.lower() and m.last_name.lower() == patient_member.last_name.lower()), None)
            if pm:
                primary_mem_id = pm.member_id

        if secondary_policy:
            sm = next((m for m in secondary_policy.members if m.first_name.lower() == patient_member.first_name.lower() and m.last_name.lower() == patient_member.last_name.lower()), None)
            if sm:
                secondary_mem_id = sm.member_id

        for line in claim.lines:
            billed_d = _d(line.billed_amount)
            tot_billed += billed_d

            pri_key = f"{primary_policy.policy_id}:{primary_mem_id}" if primary_policy else ""
            sec_key = f"{secondary_policy.policy_id}:{secondary_mem_id}" if secondary_policy else ""

            if pri_key and pri_key not in rem_indiv_ded:
                rem_indiv_ded[pri_key] = _d(primary_policy.deductible.remaining_individual)
                rem_indiv_oop[pri_key] = _d(primary_policy.remaining_out_of_pocket_max)

            if sec_key and sec_key not in rem_indiv_ded:
                rem_indiv_ded[sec_key] = _d(secondary_policy.deductible.remaining_individual)
                rem_indiv_oop[sec_key] = _d(secondary_policy.remaining_out_of_pocket_max)

            # Check medical necessity
            is_necessary, necessity_notes = self.check_medical_necessity(line.cpt_code, claim.diagnoses or [])

            # ----------------------------------------------------
            # 1. Primary Adjudication
            # ----------------------------------------------------
            is_pri_covered = False
            pri_allowed_d = billed_d
            pri_writeoff_d = Decimal("0.00")
            pri_copay_d = Decimal("0.00")
            pri_ded_d = Decimal("0.00")
            pri_coins_rate_d = Decimal("0.00")
            pri_coins_amt_d = Decimal("0.00")
            pri_paid_d = Decimal("0.00")
            pri_patient_resp_d = billed_d

            pri_rule = self.insurance_service.get_coverage_rule(primary_policy, line.cpt_code) if primary_policy else None

            if primary_policy and is_necessary and pri_rule and pri_rule.is_covered:
                is_pri_covered = True
                allowed_val = getattr(pri_rule, "allowed_amount", None)
                if allowed_val is not None and _d(allowed_val) < billed_d:
                    pri_allowed_d = _d(allowed_val)
                    pri_writeoff_d = billed_d - pri_allowed_d
                else:
                    pri_allowed_d = billed_d

                # Apply Copay
                copay_val = getattr(pri_rule, "copay", 0.0)
                try:
                    copay_float = float(copay_val)
                except Exception:
                    copay_float = 0.0

                if copay_float > 0:
                    pri_copay_d = min(pri_allowed_d, _d(copay_float))

                rem_allowed_after_copay = pri_allowed_d - pri_copay_d

                # Apply Deductible
                ded_applies = getattr(pri_rule, "deductible_applies", True)
                if ded_applies and rem_allowed_after_copay > Decimal("0.00"):
                    indiv_rem = rem_indiv_ded[pri_key]
                    fam_rem = rem_fam_ded[primary_policy.policy_id]
                    pri_ded_d = min(rem_allowed_after_copay, indiv_rem, fam_rem)
                    rem_indiv_ded[pri_key] -= pri_ded_d
                    rem_fam_ded[primary_policy.policy_id] -= pri_ded_d

                    primary_policy.deductible.remaining_individual = _f(rem_indiv_ded[pri_key])
                    primary_policy.deductible.remaining_family = _f(rem_fam_ded[primary_policy.policy_id])
                    if hasattr(self.insurance_service, "_policies") and primary_policy.policy_id in self.insurance_service._policies:
                        self.insurance_service._policies[primary_policy.policy_id].deductible.remaining_individual = _f(rem_indiv_ded[pri_key])
                        self.insurance_service._policies[primary_policy.policy_id].deductible.remaining_family = _f(rem_fam_ded[primary_policy.policy_id])

                # Apply Coinsurance
                subject_to_coins = rem_allowed_after_copay - pri_ded_d
                pri_coins_rate_d = _d(primary_policy.coinsurance.rate)
                pri_coins_amt_d = (subject_to_coins * pri_coins_rate_d).quantize(PENCE, rounding=ROUND_HALF_UP)
                pri_paid_d = subject_to_coins - pri_coins_amt_d

                # Calculate Patient Responsibility before OOPM cap
                pri_patient_resp_d = pri_copay_d + pri_ded_d + pri_coins_amt_d

                # Apply Primary OOP Maximum
                rem_oop = rem_indiv_oop[pri_key]
                if pri_patient_resp_d > rem_oop:
                    excess = pri_patient_resp_d - rem_oop
                    pri_patient_resp_d = rem_oop
                    pri_paid_d += excess
                    pri_coins_amt_d = max(Decimal("0.00"), pri_patient_resp_d - pri_copay_d - pri_ded_d)

                rem_indiv_oop[pri_key] = max(Decimal("0.00"), rem_oop - pri_patient_resp_d)

            primary_coverage = PrimaryCoverage(
                policy_id=str(primary_policy.policy_id) if primary_policy and primary_policy.policy_id else "",
                is_covered=is_pri_covered,
                allowed_amount=_f(pri_allowed_d) if pri_rule and getattr(pri_rule, "allowed_amount", None) is not None else None,
                contractual_writeoff=_f(pri_writeoff_d),
                copay_applied=_f(pri_copay_d),
                deductible_applied=_f(pri_ded_d),
                coinsurance_rate=_f(pri_coins_rate_d),
                coinsurance_amount=_f(pri_coins_amt_d),
                primary_paid=_f(pri_paid_d),
                patient_responsibility=_f(pri_patient_resp_d),
            )

            # ----------------------------------------------------
            # 2. Secondary Adjudication (Coordination of Benefits)
            # ----------------------------------------------------
            is_sec_covered = False
            sec_allowed_d = None
            sec_copay_d = Decimal("0.00")
            sec_ded_d = Decimal("0.00")
            sec_coins_rate_d = Decimal("0.00")
            sec_coins_amt_d = Decimal("0.00")
            sec_paid_d = Decimal("0.00")
            sec_patient_resp_d = pri_patient_resp_d
            notes_msg = ""

            sec_rule = self.insurance_service.get_coverage_rule(secondary_policy, line.cpt_code) if secondary_policy else None

            if not is_necessary:
                notes_msg = necessity_notes
            elif secondary_policy and is_pri_covered:
                if sec_rule and sec_rule.is_covered:
                    is_sec_covered = True
                    # Calculate secondary normal benefit if primary had not paid
                    sec_rem_ded = rem_indiv_ded[sec_key]
                    sec_ded_applied_if_primary = min(pri_allowed_d, sec_rem_ded)
                    sec_coins_rate_d = _d(secondary_policy.coinsurance.rate)
                    sec_normal_paid = ((pri_allowed_d - sec_ded_applied_if_primary) * (Decimal("1.00") - sec_coins_rate_d)).quantize(PENCE, rounding=ROUND_HALF_UP)

                    # Secondary pays lesser of remaining patient responsibility or normal benefit
                    sec_paid_d = min(pri_patient_resp_d, sec_normal_paid)
                    sec_ded_satisfied = min(pri_patient_resp_d, sec_ded_applied_if_primary)

                    rem_indiv_ded[sec_key] = max(Decimal("0.00"), sec_rem_ded - sec_ded_satisfied)
                    sec_fam = rem_fam_ded[secondary_policy.policy_id]
                    rem_fam_ded[secondary_policy.policy_id] = max(Decimal("0.00"), sec_fam - sec_ded_satisfied)

                    sec_ded_d = sec_ded_satisfied
                    sec_patient_resp_d = pri_patient_resp_d - sec_paid_d

                    secondary_policy.deductible.remaining_individual = _f(rem_indiv_ded[sec_key])
                    secondary_policy.deductible.remaining_family = _f(rem_fam_ded[secondary_policy.policy_id])
                    if hasattr(self.insurance_service, "_policies") and secondary_policy.policy_id in self.insurance_service._policies:
                        self.insurance_service._policies[secondary_policy.policy_id].deductible.remaining_individual = _f(rem_indiv_ded[sec_key])
                        self.insurance_service._policies[secondary_policy.policy_id].deductible.remaining_family = _f(rem_fam_ded[secondary_policy.policy_id])

                    # Apply secondary OOP Maximum
                    sec_oop = rem_indiv_oop[sec_key]
                    if sec_patient_resp_d > sec_oop:
                        excess = sec_patient_resp_d - sec_oop
                        sec_patient_resp_d = sec_oop
                        sec_paid_d += excess

                    rem_indiv_oop[sec_key] = max(Decimal("0.00"), sec_oop - sec_patient_resp_d)

                    notes_msg = (
                        f"Patient: {patient_name}. "
                        f"Primary paid ₹{_f(pri_paid_d):.2f}. "
                        f"Secondary coordinated and paid ₹{_f(sec_paid_d):.2f} (deductible credited: ₹{_f(sec_ded_d):.2f})."
                    )
                else:
                    notes_msg = f"Procedure not covered under secondary policy {secondary_policy.policy_id}."
            elif secondary_policy and not is_pri_covered:
                # Primary excluded procedure; secondary processes as primary
                if sec_rule and sec_rule.is_covered:
                    is_sec_covered = True
                    sec_rem_ded = rem_indiv_ded[sec_key]
                    sec_ded_d = min(billed_d, sec_rem_ded)
                    rem_indiv_ded[sec_key] = max(Decimal("0.00"), sec_rem_ded - sec_ded_d)
                    sec_fam = rem_fam_ded[secondary_policy.policy_id]
                    rem_fam_ded[secondary_policy.policy_id] = max(Decimal("0.00"), sec_fam - sec_ded_d)

                    sec_coins_rate_d = _d(secondary_policy.coinsurance.rate)
                    subject_to_coins = billed_d - sec_ded_d
                    sec_coins_amt_d = (subject_to_coins * sec_coins_rate_d).quantize(PENCE, rounding=ROUND_HALF_UP)
                    sec_paid_d = subject_to_coins - sec_coins_amt_d
                    sec_patient_resp_d = sec_ded_d + sec_coins_amt_d

                    sec_oop = rem_indiv_oop[sec_key]
                    if sec_patient_resp_d > sec_oop:
                        excess = sec_patient_resp_d - sec_oop
                        sec_patient_resp_d = sec_oop
                        sec_paid_d += excess
                        sec_coins_amt_d = max(Decimal("0.00"), sec_patient_resp_d - sec_ded_d)

                    rem_indiv_oop[sec_key] = max(Decimal("0.00"), sec_oop - sec_patient_resp_d)
                    notes_msg = f"Patient: {patient_name}. Excluded by primary. Secondary paid ₹{_f(sec_paid_d):.2f}."
                else:
                    notes_msg = "Procedure excluded by both primary and secondary policies."
            else:
                notes_msg = f"Single coverage only. Patient responsibility: ₹{_f(pri_patient_resp_d):.2f}."

            secondary_coverage = SecondaryCoverage(
                policy_id=str(secondary_policy.policy_id) if secondary_policy and secondary_policy.policy_id else "",
                is_covered=is_sec_covered,
                allowed_amount=sec_allowed_d,
                copay_applied=_f(sec_copay_d),
                deductible_applied=_f(sec_ded_d),
                coinsurance_rate=_f(sec_coins_rate_d),
                coinsurance_amount=_f(sec_coins_amt_d),
                secondary_paid=_f(sec_paid_d),
                patient_responsibility=_f(sec_patient_resp_d),
            )

            # ----------------------------------------------------
            # 3. Line-Level Financial Invariant Verification
            # ----------------------------------------------------
            line_sum = pri_paid_d + sec_paid_d + sec_patient_resp_d + pri_writeoff_d
            if line_sum != billed_d:
                raise ArithmeticError(
                    f"Financial conservation law violated on CPT {line.cpt_code}: "
                    f"primary_paid ({pri_paid_d}) + secondary_paid ({sec_paid_d}) + "
                    f"patient_resp ({sec_patient_resp_d}) + writeoff ({pri_writeoff_d}) = {line_sum} != billed ({billed_d})"
                )

            remaining_balance = RemainingBalance(
                billed_amount=_f(billed_d),
                primary_paid=_f(pri_paid_d),
                secondary_paid=_f(sec_paid_d),
                patient_responsibility=_f(sec_patient_resp_d),
                notes=notes_msg,
            )

            tot_primary_paid += pri_paid_d
            tot_secondary_paid += sec_paid_d
            tot_patient_resp += sec_patient_resp_d

            lines_coverage.append(
                ClaimLineCoverage(
                    cpt_code=line.cpt_code,
                    billed_amount=_f(billed_d),
                    primary_coverage=primary_coverage,
                    secondary_coverage=secondary_coverage,
                    remaining_balance=remaining_balance,
                )
            )

        return COBDecision(
            claim_id=claim.claim_id,
            patient_name=patient_name,
            primary_policy_id=str(primary_policy.policy_id) if primary_policy and primary_policy.policy_id else None,
            primary_provider=str(primary_policy.provider_name) if primary_policy and primary_policy.provider_name else None,
            secondary_policy_id=str(secondary_policy.policy_id) if secondary_policy and secondary_policy.policy_id else None,
            secondary_provider=str(secondary_policy.provider_name) if secondary_policy and secondary_policy.provider_name else None,
            lines_coverage=lines_coverage,
            total_billed=_f(tot_billed),
            total_primary_paid=_f(tot_primary_paid),
            total_secondary_paid=_f(tot_secondary_paid),
            total_patient_responsibility=_f(tot_patient_resp),
        )

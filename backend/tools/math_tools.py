import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def calculate_deductible_share(amount: float, remaining_deductible: float) -> Dict[str, float]:
    """
    Applies deductible to an allowed procedure amount.
    Returns applied deductible and remaining amount eligible for coinsurance.
    """
    amount = float(amount)
    remaining_deductible = float(remaining_deductible)
    
    applied_deductible = min(amount, remaining_deductible)
    amount_after_deductible = round(amount - applied_deductible, 2)
    new_remaining_deductible = round(remaining_deductible - applied_deductible, 2)
    
    return {
        "applied_deductible": round(applied_deductible, 2),
        "amount_after_deductible": amount_after_deductible,
        "new_remaining_deductible": new_remaining_deductible,
    }


def calculate_coinsurance_share(amount: float, coinsurance_rate: float) -> Dict[str, float]:
    """
    Calculates patient and plan coinsurance shares based on coinsurance rate (0.0 - 1.0).
    For example, rate=0.2 means patient pays 20%, plan pays 80%.
    """
    amount = float(amount)
    coinsurance_rate = float(coinsurance_rate)
    
    patient_coinsurance = round(amount * coinsurance_rate, 2)
    plan_coinsurance = round(amount - patient_coinsurance, 2)
    
    return {
        "patient_coinsurance": patient_coinsurance,
        "plan_coinsurance": plan_coinsurance,
    }


def adjudicate_line_financials(
    billed_amount: float,
    allowed_amount: float,
    remaining_deductible: float,
    coinsurance_rate: float,
    copay_amount: float = 0.0
) -> Dict[str, float]:
    """
    Adjudicates a single claim line for primary insurance using deterministic arithmetic tools.
    """
    billed = float(billed_amount)
    allowed = float(allowed_amount)
    rem_ded = float(remaining_deductible)
    co_rate = float(coinsurance_rate)
    copay = float(copay_amount)
    
    contractual_adjustment = round(max(0.0, billed - allowed), 2)
    
    # 1. Copay
    copay_applied = min(allowed, copay)
    amount_after_copay = max(0.0, allowed - copay_applied)
    
    # 2. Deductible
    ded_result = calculate_deductible_share(amount_after_copay, rem_ded)
    applied_ded = ded_result["applied_deductible"]
    amount_after_ded = ded_result["amount_after_deductible"]
    
    # 3. Coinsurance
    coins_result = calculate_coinsurance_share(amount_after_ded, co_rate)
    patient_coins = coins_result["patient_coinsurance"]
    plan_paid = coins_result["plan_coinsurance"]
    
    patient_total_resp = round(copay_applied + applied_ded + patient_coins, 2)
    
    return {
        "billed_amount": round(billed, 2),
        "allowed_amount": round(allowed, 2),
        "contractual_adjustment": contractual_adjustment,
        "copay_applied": round(copay_applied, 2),
        "deductible_applied": round(applied_ded, 2),
        "patient_coinsurance": patient_coins,
        "plan_paid": plan_paid,
        "patient_total_responsibility": patient_total_resp,
        "updated_remaining_deductible": ded_result["new_remaining_deductible"],
    }


def calculate_cob_coordination(
    billed_amount: float,
    primary_allowed: float,
    primary_paid: float,
    secondary_allowed: float,
    secondary_coinsurance_rate: float,
    secondary_remaining_deductible: float
) -> Dict[str, float]:
    """
    Calculates Coordination of Benefits (COB) secondary payer liability using non-duplication math rules.
    Secondary payer covers up to what it would have paid as primary, minus primary payment, capped at patient liability.
    """
    billed = float(billed_amount)
    pri_allowed = float(primary_allowed)
    pri_paid = float(primary_paid)
    sec_allowed = float(secondary_allowed)
    sec_co_rate = float(secondary_coinsurance_rate)
    sec_rem_ded = float(secondary_remaining_deductible)
    
    # Patient liability remaining after primary insurance
    primary_patient_liability = max(0.0, pri_allowed - pri_paid)
    
    # What secondary would pay as primary
    sec_ded_res = calculate_deductible_share(sec_allowed, sec_rem_ded)
    sec_applied_ded = sec_ded_res["applied_deductible"]
    sec_after_ded = sec_ded_res["amount_after_deductible"]
    sec_coins_res = calculate_coinsurance_share(sec_after_ded, sec_co_rate)
    sec_would_pay_primary = sec_coins_res["plan_coinsurance"]
    
    # Secondary actual payment is lesser of secondary would pay vs primary patient liability
    secondary_paid = round(min(sec_would_pay_primary, primary_patient_liability), 2)
    
    # Final patient remaining liability after COB
    final_patient_responsibility = round(max(0.0, primary_patient_liability - secondary_paid), 2)
    
    return {
        "billed_amount": round(billed, 2),
        "primary_allowed": round(pri_allowed, 2),
        "primary_paid": round(pri_paid, 2),
        "primary_patient_liability": round(primary_patient_liability, 2),
        "secondary_allowed": round(sec_allowed, 2),
        "secondary_would_pay_primary": round(sec_would_pay_primary, 2),
        "secondary_paid": round(secondary_paid, 2),
        "final_patient_responsibility": final_patient_responsibility,
    }


class FinancialMathTool:
    """Agent tool wrapper for invoking deterministic math functions."""
    
    def __init__(self):
        self.name = "FinancialMathTool"
        self.description = "Executes deterministic medical insurance financial math calculations."
        
    def calculate_line(
        self,
        billed_amount: float,
        allowed_amount: float,
        remaining_deductible: float,
        coinsurance_rate: float,
        copay_amount: float = 0.0
    ) -> Dict[str, float]:
        """Calculates claim line adjudication breakdown."""
        return adjudicate_line_financials(
            billed_amount=billed_amount,
            allowed_amount=allowed_amount,
            remaining_deductible=remaining_deductible,
            coinsurance_rate=coinsurance_rate,
            copay_amount=copay_amount
        )

    def calculate_cob(
        self,
        billed_amount: float,
        primary_allowed: float,
        primary_paid: float,
        secondary_allowed: float,
        secondary_coinsurance_rate: float,
        secondary_remaining_deductible: float
    ) -> Dict[str, float]:
        """Calculates COB secondary payment allocation."""
        return calculate_cob_coordination(
            billed_amount=billed_amount,
            primary_allowed=primary_allowed,
            primary_paid=primary_paid,
            secondary_allowed=secondary_allowed,
            secondary_coinsurance_rate=secondary_coinsurance_rate,
            secondary_remaining_deductible=secondary_remaining_deductible
        )

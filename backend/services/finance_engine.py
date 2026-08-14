import uuid
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Union

from app.schemas.cob_engine import COBDecision
from app.schemas.finance_engine import (
    PaymentAllocation,
    PatientResponsibility,
    CostSummary,
    FinancialBreakdown,
    FinancialReport,
)

logger = logging.getLogger(__name__)

PENCE = Decimal("0.01")


def _d(value: Union[float, int, str, Decimal, None]) -> Decimal:
    """Safely converts any numeric input to a 2-decimal rounded Decimal."""
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
    """Converts a Decimal to float rounded to 2 decimal places."""
    return float(d.quantize(PENCE, rounding=ROUND_HALF_UP))


class FinanceEngine:
    """Engine responsible for translating claim coordination results (COBDecision) into audited financial reports with Decimal precision."""

    def generate_financial_breakdown(self, cob_decision: COBDecision) -> FinancialReport:
        """Processes a Coordination of Benefits decision and structures it into a comprehensive, conservation-verified FinancialReport."""
        logger.info(f"Generating financial breakdown for claim {cob_decision.claim_id}")

        allocations: List[PaymentAllocation] = []
        total_billed_d = Decimal("0.00")
        total_primary_paid_d = Decimal("0.00")
        total_secondary_paid_d = Decimal("0.00")
        total_deductible_paid_d = Decimal("0.00")
        total_coinsurance_paid_d = Decimal("0.00")
        total_patient_responsibility_d = Decimal("0.00")
        total_writeoff_d = Decimal("0.00")
        denial_notes = []

        for line_cov in cob_decision.lines_coverage:
            cpt = line_cov.cpt_code
            billed_d = _d(line_cov.billed_amount)
            pri_paid_d = _d(line_cov.primary_coverage.primary_paid)
            sec_paid_d = _d(line_cov.secondary_coverage.secondary_paid)
            pat_resp_d = _d(line_cov.remaining_balance.patient_responsibility)
            writeoff_d = _d(line_cov.primary_coverage.contractual_writeoff if hasattr(line_cov.primary_coverage, "contractual_writeoff") else 0.0)

            # Gather denial notes
            notes = line_cov.remaining_balance.notes
            if notes and ("not medically necessary" in notes.lower() or "not covered" in notes.lower() or "denied" in notes.lower()):
                denial_notes.append(notes)

            # Calculate deductible vs coinsurance patient out-of-pocket splits using exact policy-applied values
            patient_ded_applied_d = Decimal("0.00")
            patient_coins_applied_d = Decimal("0.00")

            if line_cov.primary_coverage.is_covered:
                pri_ded_d = _d(line_cov.primary_coverage.deductible_applied)
                if pat_resp_d <= pri_ded_d:
                    patient_ded_applied_d = pat_resp_d
                    patient_coins_applied_d = Decimal("0.00")
                else:
                    patient_ded_applied_d = pri_ded_d
                    patient_coins_applied_d = pat_resp_d - pri_ded_d
            elif line_cov.secondary_coverage.is_covered:
                sec_ded_d = _d(line_cov.secondary_coverage.deductible_applied)
                if pat_resp_d <= sec_ded_d:
                    patient_ded_applied_d = pat_resp_d
                    patient_coins_applied_d = Decimal("0.00")
                else:
                    patient_ded_applied_d = sec_ded_d
                    patient_coins_applied_d = pat_resp_d - sec_ded_d
            else:
                # Neither covers: full patient responsibility is treated as coins/uncovered balance
                patient_coins_applied_d = pat_resp_d

            # Accumulate totals in Decimal arithmetic
            total_billed_d += billed_d
            total_primary_paid_d += pri_paid_d
            total_secondary_paid_d += sec_paid_d
            total_deductible_paid_d += patient_ded_applied_d
            total_coinsurance_paid_d += patient_coins_applied_d
            total_patient_responsibility_d += pat_resp_d
            total_writeoff_d += writeoff_d

            allocations.append(
                PaymentAllocation(
                    cpt_code=cpt,
                    billed_amount=_f(billed_d),
                    primary_paid=_f(pri_paid_d),
                    secondary_paid=_f(sec_paid_d),
                    patient_deductible_applied=_f(patient_ded_applied_d),
                    patient_coinsurance_applied=_f(patient_coins_applied_d),
                    patient_responsibility=_f(pat_resp_d),
                )
            )

        # Verify aggregate financial conservation
        aggregate_sum_d = total_primary_paid_d + total_secondary_paid_d + total_patient_responsibility_d + total_writeoff_d
        if total_billed_d > Decimal("0.00") and aggregate_sum_d != total_billed_d:
            raise ArithmeticError(
                f"Financial conservation law violated on aggregate summary: "
                f"primary_paid ({total_primary_paid_d}) + secondary_paid ({total_secondary_paid_d}) + "
                f"patient_resp ({total_patient_responsibility_d}) + writeoff ({total_writeoff_d}) = {aggregate_sum_d} != billed ({total_billed_d})"
            )

        total_insurer_paid_d = total_primary_paid_d + total_secondary_paid_d
        total_savings_d = total_billed_d - total_patient_responsibility_d

        # Assemble summary message
        primary_name = cob_decision.primary_provider or "Primary Insurer"
        secondary_name = cob_decision.secondary_provider or "Secondary Insurer"
        
        explanation = (
            f"The total billed amount of ₹{_f(total_billed_d):.2f} was coordinated across dual coverage. "
            f"{primary_name} paid ₹{_f(total_primary_paid_d):.2f}. "
        )
        if cob_decision.secondary_policy_id:
            explanation += f"{secondary_name} coordinated and paid ₹{_f(total_secondary_paid_d):.2f}. "
        
        explanation += (
            f"The patient out-of-pocket responsibility is ₹{_f(total_patient_responsibility_d):.2f}, "
            f"comprising ₹{_f(total_deductible_paid_d):.2f} towards deductibles and ₹{_f(total_coinsurance_paid_d):.2f} towards coinsurance."
        )

        if denial_notes:
            unique_denials = []
            for note in denial_notes:
                if note not in unique_denials:
                    unique_denials.append(note)
            explanation += " Denials/Exclusions: " + " ".join(unique_denials)

        patient_responsibility = PatientResponsibility(
            total_deductible=_f(total_deductible_paid_d),
            total_coinsurance=_f(total_coinsurance_paid_d),
            total_responsibility=_f(total_patient_responsibility_d),
            explanation_notes=explanation,
        )

        summary = CostSummary(
            total_billed=_f(total_billed_d),
            total_primary_paid=_f(total_primary_paid_d),
            total_secondary_paid=_f(total_secondary_paid_d),
            total_insurer_paid=_f(total_insurer_paid_d),
            total_patient_responsibility=_f(total_patient_responsibility_d),
            total_savings=_f(total_savings_d),
        )

        breakdown = FinancialBreakdown(
            allocations=allocations,
            patient_responsibility=patient_responsibility,
            summary=summary,
        )

        report_id = f"FIN-REPORT-{uuid.uuid4().hex[:8].upper()}"
        generated_at = datetime.utcnow().isoformat() + "Z"

        return FinancialReport(
            report_id=report_id,
            claim_id=cob_decision.claim_id,
            patient_name=cob_decision.patient_name,
            generated_at=generated_at,
            primary_policy_id=cob_decision.primary_policy_id,
            secondary_policy_id=cob_decision.secondary_policy_id,
            breakdown=breakdown,
        )

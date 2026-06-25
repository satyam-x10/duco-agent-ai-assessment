import uuid
import logging
from datetime import datetime

from app.schemas.cob_engine import COBDecision
from app.schemas.finance_engine import (
    PaymentAllocation,
    PatientResponsibility,
    CostSummary,
    FinancialBreakdown,
    FinancialReport,
)

logger = logging.getLogger(__name__)


class FinanceEngine:
    """Engine responsible for translating claim coordination results (COBDecision) into audited financial reports."""

    def generate_financial_breakdown(self, cob_decision: COBDecision) -> FinancialReport:
        """Processes a Coordination of Benefits decision and structures it into a comprehensive FinancialReport."""
        logger.info(f"Generating financial breakdown for claim {cob_decision.claim_id}")

        allocations: List[PaymentAllocation] = []
        total_billed = 0.0
        total_primary_paid = 0.0
        total_secondary_paid = 0.0
        total_deductible_paid = 0.0
        total_coinsurance_paid = 0.0
        total_patient_responsibility = 0.0

        for line_cov in cob_decision.lines_coverage:
            cpt = line_cov.cpt_code
            billed = line_cov.billed_amount
            pri_paid = line_cov.primary_coverage.primary_paid
            sec_paid = line_cov.secondary_coverage.secondary_paid
            pat_resp = line_cov.remaining_balance.patient_responsibility

            # Calculate deductible vs coinsurance patient out-of-pocket splits
            patient_ded_applied = 0.0
            patient_coins_applied = 0.0

            if line_cov.primary_coverage.is_covered:
                pri_ded = line_cov.primary_coverage.deductible_applied
                if pat_resp <= pri_ded:
                    patient_ded_applied = pat_resp
                else:
                    patient_ded_applied = pri_ded
                    patient_coins_applied = pat_resp - pri_ded
            elif line_cov.secondary_coverage.is_covered:
                sec_ded = line_cov.secondary_coverage.deductible_applied
                if pat_resp <= sec_ded:
                    patient_ded_applied = pat_resp
                else:
                    patient_ded_applied = sec_ded
                    patient_coins_applied = pat_resp - sec_ded
            else:
                # Neither covers: full patient responsibility is treated as coins/uncovered balance
                patient_coins_applied = pat_resp

            # Clean float rounding
            patient_ded_applied = round(patient_ded_applied, 2)
            patient_coins_applied = round(patient_coins_applied, 2)

            total_billed += billed
            total_primary_paid += pri_paid
            total_secondary_paid += sec_paid
            total_deductible_paid += patient_ded_applied
            total_coinsurance_paid += patient_coins_applied
            total_patient_responsibility += pat_resp

            allocations.append(
                PaymentAllocation(
                    cpt_code=cpt,
                    billed_amount=billed,
                    primary_paid=pri_paid,
                    secondary_paid=sec_paid,
                    patient_deductible_applied=patient_ded_applied,
                    patient_coinsurance_applied=patient_coins_applied,
                    patient_responsibility=pat_resp,
                )
            )

        # Round totals
        total_billed = round(total_billed, 2)
        total_primary_paid = round(total_primary_paid, 2)
        total_secondary_paid = round(total_secondary_paid, 2)
        total_insurer_paid = round(total_primary_paid + total_secondary_paid, 2)
        total_deductible_paid = round(total_deductible_paid, 2)
        total_coinsurance_paid = round(total_coinsurance_paid, 2)
        total_patient_responsibility = round(total_patient_responsibility, 2)
        total_savings = round(total_billed - total_patient_responsibility, 2)

        # Assemble summary message
        primary_name = cob_decision.primary_provider or "Primary Insurer"
        secondary_name = cob_decision.secondary_provider or "Secondary Insurer"
        
        explanation = (
            f"The total billed amount of ${total_billed:.2f} was coordinated across dual coverage. "
            f"{primary_name} paid ${total_primary_paid:.2f}. "
        )
        if cob_decision.secondary_policy_id:
            explanation += f"{secondary_name} coordinated and paid ${total_secondary_paid:.2f}. "
        
        explanation += (
            f"The patient out-of-pocket responsibility is ${total_patient_responsibility:.2f}, "
            f"comprising ${total_deductible_paid:.2f} towards deductibles and ${total_coinsurance_paid:.2f} towards coinsurance."
        )

        patient_responsibility = PatientResponsibility(
            total_deductible=total_deductible_paid,
            total_coinsurance=total_coinsurance_paid,
            total_responsibility=total_patient_responsibility,
            explanation_notes=explanation,
        )

        summary = CostSummary(
            total_billed=total_billed,
            total_primary_paid=total_primary_paid,
            total_secondary_paid=total_secondary_paid,
            total_insurer_paid=total_insurer_paid,
            total_patient_responsibility=total_patient_responsibility,
            total_savings=total_savings,
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

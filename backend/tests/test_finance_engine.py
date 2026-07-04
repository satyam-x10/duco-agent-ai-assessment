import pytest
from app.schemas.cob_engine import (
    COBDecision,
    ClaimLineCoverage,
    PrimaryCoverage,
    SecondaryCoverage,
    RemainingBalance,
)
from app.schemas.finance_engine import FinancialReport
from services.finance_engine import FinanceEngine


@pytest.fixture
def finance_engine():
    return FinanceEngine()


def test_finance_engine_aggregation(finance_engine):
    """Verify that FinanceEngine aggregates billed charges, payments, and patient costs correctly."""
    # Build a mock COBDecision representing a physical therapy evaluation (CPT 97161)
    cob_decision = COBDecision(
        claim_id="CLAIM-PT",
        patient_name="Priya Sen",
        primary_policy_id="BS-120-BLUE",
        primary_provider="BlueShield Cross",
        secondary_policy_id="UH-990-GOLD",
        secondary_provider="UnitedHealth",
        lines_coverage=[
            ClaimLineCoverage(
                cpt_code="97161",
                billed_amount=20000.0,
                primary_coverage=PrimaryCoverage(
                    policy_id="BS-120-BLUE",
                    is_covered=True,
                    deductible_applied=20000.0,
                    coinsurance_rate=0.20,
                    coinsurance_amount=0.0,
                    primary_paid=0.0,
                    patient_responsibility=20000.0,
                ),
                secondary_coverage=SecondaryCoverage(
                    policy_id="UH-990-GOLD",
                    is_covered=True,
                    deductible_applied=20000.0,
                    coinsurance_rate=0.10,
                    coinsurance_amount=0.0,
                    secondary_paid=0.0,
                    patient_responsibility=20000.0,
                ),
                remaining_balance=RemainingBalance(
                    billed_amount=20000.0,
                    primary_paid=0.0,
                    secondary_paid=0.0,
                    patient_responsibility=20000.0,
                ),
            )
        ],
        total_billed=20000.0,
        total_primary_paid=0.0,
        total_secondary_paid=0.0,
        total_patient_responsibility=20000.0,
    )

    report = finance_engine.generate_financial_breakdown(cob_decision)

    assert isinstance(report, FinancialReport)
    assert report.claim_id == "CLAIM-PT"
    assert report.patient_name == "Priya Sen"
    assert report.primary_policy_id == "BS-120-BLUE"
    assert report.secondary_policy_id == "UH-990-GOLD"

    breakdown = report.breakdown
    assert breakdown.summary.total_billed == 20000.0
    assert breakdown.summary.total_primary_paid == 0.0
    assert breakdown.summary.total_secondary_paid == 0.0
    assert breakdown.summary.total_insurer_paid == 0.0
    assert breakdown.summary.total_patient_responsibility == 20000.0
    assert breakdown.summary.total_savings == 0.0

    # Allocation checks:
    # Billed: ₹20000.00, Insurer Paid: ₹0.00.
    # Patient responsibility: ₹20000.00.
    # Since ₹20000.00 <= ₹20000.00 (primary deductible applied), it is attributed entirely to deductible.
    alloc = breakdown.allocations[0]
    assert alloc.cpt_code == "97161"
    assert alloc.billed_amount == 20000.0
    assert alloc.primary_paid == 0.0
    assert alloc.secondary_paid == 0.0
    assert alloc.patient_deductible_applied == 20000.0
    assert alloc.patient_coinsurance_applied == 0.0
    assert alloc.patient_responsibility == 20000.0

    assert breakdown.patient_responsibility.total_deductible == 20000.0
    assert breakdown.patient_responsibility.total_coinsurance == 0.0
    assert breakdown.patient_responsibility.total_responsibility == 20000.0
    assert "comprising ₹20000.00 towards deductibles" in breakdown.patient_responsibility.explanation_notes


def test_finance_engine_split_coinsurance(finance_engine):
    """Verify out-of-pocket cost splits when patient responsibility exceeds the primary deductible applied."""
    cob_decision = COBDecision(
        claim_id="CLAIM-SURGERY",
        patient_name="Aarav Sen",
        primary_policy_id="BS-120-BLUE",
        primary_provider="BlueShield Cross",
        lines_coverage=[
            ClaimLineCoverage(
                cpt_code="29881",
                billed_amount=100000.0,
                primary_coverage=PrimaryCoverage(
                    policy_id="BS-120-BLUE",
                    is_covered=True,
                    deductible_applied=10000.0,
                    coinsurance_rate=0.20,
                    coinsurance_amount=18000.0,
                    primary_paid=72000.0,
                    patient_responsibility=28000.0,
                ),
                secondary_coverage=SecondaryCoverage(
                    policy_id="",
                    is_covered=False,
                    deductible_applied=0.0,
                    coinsurance_rate=0.0,
                    coinsurance_amount=0.0,
                    secondary_paid=0.0,
                    patient_responsibility=28000.0,
                ),
                remaining_balance=RemainingBalance(
                    billed_amount=100000.0,
                    primary_paid=72000.0,
                    secondary_paid=0.0,
                    patient_responsibility=28000.0,
                ),
            )
        ],
        total_billed=100000.0,
        total_primary_paid=72000.0,
        total_secondary_paid=0.0,
        total_patient_responsibility=28000.0,
    )

    report = finance_engine.generate_financial_breakdown(cob_decision)

    breakdown = report.breakdown
    # Deductible applied on primary: ₹10000.00
    # Patient responsibility: ₹28000.00
    # ₹10000.00 goes to deductible, remaining ₹18000.00 goes to coinsurance.
    alloc = breakdown.allocations[0]
    assert alloc.patient_deductible_applied == 10000.0
    assert alloc.patient_coinsurance_applied == 18000.0
    assert alloc.patient_responsibility == 28000.0

    assert breakdown.patient_responsibility.total_deductible == 10000.0
    assert breakdown.patient_responsibility.total_coinsurance == 18000.0


def test_finance_engine_secondary_only_coverage(finance_engine):
    """Verify splits when primary excludes a procedure but secondary covers it."""
    cob_decision = COBDecision(
        claim_id="CLAIM-SEC-ONLY",
        patient_name="Jane Doe",
        primary_policy_id="POLICY-A",
        primary_provider="Insurer A",
        secondary_policy_id="POLICY-B",
        secondary_provider="Insurer B",
        lines_coverage=[
            ClaimLineCoverage(
                cpt_code="99999",
                billed_amount=20000.0,
                primary_coverage=PrimaryCoverage(
                    policy_id="POLICY-A",
                    is_covered=False,
                    deductible_applied=0.0,
                    coinsurance_rate=0.0,
                    coinsurance_amount=0.0,
                    primary_paid=0.0,
                    patient_responsibility=20000.0,
                ),
                secondary_coverage=SecondaryCoverage(
                    policy_id="POLICY-B",
                    is_covered=True,
                    deductible_applied=5000.0,
                    coinsurance_rate=0.10,
                    coinsurance_amount=1500.0,
                    secondary_paid=13500.0,
                    patient_responsibility=6500.0,
                ),
                remaining_balance=RemainingBalance(
                    billed_amount=20000.0,
                    primary_paid=0.0,
                    secondary_paid=13500.0,
                    patient_responsibility=6500.0,
                ),
            )
        ],
        total_billed=20000.0,
        total_primary_paid=0.0,
        total_secondary_paid=13500.0,
        total_patient_responsibility=6500.0,
    )

    report = finance_engine.generate_financial_breakdown(cob_decision)

    breakdown = report.breakdown
    # Primary excluded. Secondary covered, applying ₹5000 deductible.
    # Out of pocket patient responsibility: ₹6500.00.
    # ₹5000.00 goes to deductible, remaining ₹1500.00 goes to coinsurance.
    alloc = breakdown.allocations[0]
    assert alloc.patient_deductible_applied == 5000.0
    assert alloc.patient_coinsurance_applied == 1500.0
    assert alloc.patient_responsibility == 6500.0

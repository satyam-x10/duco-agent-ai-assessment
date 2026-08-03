import pytest
from tools.math_tools import (
    calculate_deductible_share,
    calculate_coinsurance_share,
    adjudicate_line_financials,
    calculate_cob_coordination,
    FinancialMathTool,
)

def test_calculate_deductible_share():
    res = calculate_deductible_share(amount=500.0, remaining_deductible=200.0)
    assert res["applied_deductible"] == 200.0
    assert res["amount_after_deductible"] == 300.0
    assert res["new_remaining_deductible"] == 0.0

def test_calculate_coinsurance_share():
    res = calculate_coinsurance_share(amount=300.0, coinsurance_rate=0.2)
    assert res["patient_coinsurance"] == 60.0
    assert res["plan_coinsurance"] == 240.0

def test_adjudicate_line_financials():
    res = adjudicate_line_financials(
        billed_amount=600.0,
        allowed_amount=500.0,
        remaining_deductible=100.0,
        coinsurance_rate=0.2,
        copay_amount=25.0
    )
    assert res["contractual_adjustment"] == 100.0
    assert res["copay_applied"] == 25.0
    assert res["deductible_applied"] == 100.0
    assert res["patient_coinsurance"] == 75.0  # 20% of (475-100 = 375) = 75
    assert res["plan_paid"] == 300.0          # 80% of 375 = 300
    assert res["patient_total_responsibility"] == 200.0 # 25 + 100 + 75 = 200

def test_calculate_cob_coordination():
    res = calculate_cob_coordination(
        billed_amount=1000.0,
        primary_allowed=800.0,
        primary_paid=500.0,
        secondary_allowed=800.0,
        secondary_coinsurance_rate=0.1,
        secondary_remaining_deductible=0.0
    )
    # primary patient liability = 800 - 500 = 300
    # secondary as primary = 90% of 800 = 720
    # secondary paid = min(720, 300) = 300
    # final patient resp = 0
    assert res["primary_patient_liability"] == 300.0
    assert res["secondary_paid"] == 300.0
    assert res["final_patient_responsibility"] == 0.0

def test_financial_math_tool_class():
    tool = FinancialMathTool()
    line_res = tool.calculate_line(
        billed_amount=400.0,
        allowed_amount=300.0,
        remaining_deductible=0.0,
        coinsurance_rate=0.2
    )
    assert line_res["plan_paid"] == 240.0
    assert line_res["patient_total_responsibility"] == 60.0

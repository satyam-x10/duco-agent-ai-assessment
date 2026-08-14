import pytest

from app.core.adk import SharedWorkflowState
from app.schemas.cob_engine import Claim, ClaimLine
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from app.schemas.preauth import PreAuthResponse
from services.cob_engine import COBEngine
from services.insurance_engine import InsuranceService
from services.preauth import PreAuthorizationService


@pytest.fixture
def preauth_service():
    return PreAuthorizationService()


def _adjudicated_state(*, dual_coverage: bool) -> SharedWorkflowState:
    insurance = InsuranceService()
    if not dual_coverage:
        insurance._policies.pop("UH-990-GOLD")

    member_id = "98765-02"
    patient_name = "Aarav Sen"
    line = ClaimLine(
        cpt_code="29888",
        billed_amount=350000.0,
        member_id=member_id,
        patient_name=patient_name,
        diagnoses=["S83.511A"],
        source_document="surgeon_estimate",
        source_evidence="CPT 29888 - INR 350000.00",
    )
    decision = COBEngine(insurance).coordinate_benefits(
        Claim(
            claim_id="TEST-100",
            member_id=member_id,
            lines=[line],
            diagnoses=["S83.511A"],
        )
    )
    state = SharedWorkflowState(
        claim_id="TEST-100",
        member_id=member_id,
        patient_name=patient_name,
        claim_lines=[line],
        cob_decision=decision,
        coding_result=CodingResult(
            diagnoses=[Diagnosis(code="S83.511A", description="ACL injury", confidence=1.0)],
            procedures=[Procedure(code="29888", description="ACL reconstruction", confidence=1.0)],
        ),
        primary_policy=insurance._policies["BS-120-BLUE"],
        secondary_policy=insurance._policies.get("UH-990-GOLD"),
    )
    return state


def test_generate_separate_source_grounded_letters_for_both_plans(preauth_service):
    state = _adjudicated_state(dual_coverage=True)

    response = preauth_service.generate_letters(state)

    assert isinstance(response, PreAuthResponse)
    assert response.claim_id == "TEST-100"
    assert len(response.letters) == 2
    assert {letter.insurer_name for letter in response.letters} == {"BlueShield Cross", "UnitedHealth"}

    blue = next(letter for letter in response.letters if letter.insurer_name == "BlueShield Cross")
    united = next(letter for letter in response.letters if letter.insurer_name == "UnitedHealth")
    assert "DRAFT FOR CLINICIAN REVIEW" in blue.letter_content
    assert "**Member ID:** 98765-02" in blue.letter_content
    assert "**Member ID:** 12345-03" in united.letter_content
    assert "| `29888` | ACL reconstruction | INR 350,000.00 | surgeon_estimate |" in blue.letter_content
    assert "S83.511A" in blue.letter_content
    assert "Dr. Sarah Jenkins" not in blue.letter_content
    assert "clinician completion required" in blue.letter_content


def test_generate_one_letter_for_single_coverage(preauth_service):
    state = _adjudicated_state(dual_coverage=False)

    response = preauth_service.generate_letters(state)

    assert len(response.letters) == 1
    assert response.letters[0].insurer_name == "BlueShield Cross"

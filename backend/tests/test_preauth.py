import pytest
from app.core.adk import SharedWorkflowState
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from app.schemas.preauth import PreAuthResponse
from services.insurance_engine import InsuranceService
from services.preauth import PreAuthorizationService


@pytest.fixture
def preauth_service():
    return PreAuthorizationService()


@pytest.fixture
def mock_insurance_service():
    return InsuranceService()


def test_generate_letters_dual_coverage(preauth_service, mock_insurance_service):
    """Verify that PreAuthorizationService generates professional request letters for both primary and secondary insurers."""
    # Set up SharedWorkflowState for Priya Sen (Member 98765)
    state = SharedWorkflowState(claim_id="TEST-100", member_id="98765")
    
    # Load policies
    state.primary_policy = mock_insurance_service._policies["BS-120-BLUE"]
    state.secondary_policy = mock_insurance_service._policies["UH-990-GOLD"]
    
    # Inject mock coding result
    state.coding_result = CodingResult(
        diagnoses=[
            Diagnosis(code="M23.231", description="Tear of meniscus", confidence=0.98)
        ],
        procedures=[
            Procedure(code="97161", description="PT Evaluation", confidence=0.95),
            Procedure(code="29881", description="Arthroscopy knee meniscus repair", confidence=0.97)
        ]
    )

    response = preauth_service.generate_letters(state)

    assert isinstance(response, PreAuthResponse)
    assert response.claim_id == "TEST-100"
    assert len(response.letters) == 2

    # Insurer 1: BlueShield
    letter1 = response.letters[0]
    assert letter1.insurer_name == "BlueShield Cross"
    assert letter1.policy_id == "BS-120-BLUE"
    assert letter1.patient_name == "Priya Sen"
    
    content1 = letter1.letter_content
    assert "Prior Authorization Department, BlueShield Cross" in content1
    assert "Patient Name:** Priya Sen" in content1
    assert "Date of Birth:** 1985-04-12" in content1
    assert "Member ID:** 98765" in content1
    assert "Dr. Sarah Jenkins, MD" in content1
    assert "1982736450" in content1
    assert "M23.231" in content1
    assert "Tear of meniscus" in content1
    assert "97161" in content1
    assert "29881" in content1
    assert "Estimated Billed" in content1
    
    # Verify pre-auth rules resolved under BS-120-BLUE
    # CPT 29881 requires preauth on BlueShield (YES (Required))
    # CPT 97161 does not (No (Covered))
    assert "| `29881` | Arthroscopy knee meniscus repair | ₹8,900.00 | YES (Required) |" in content1
    assert "| `97161` | PT Evaluation | ₹650.00 | No (Covered) |" in content1

    # Insurer 2: UnitedHealth
    letter2 = response.letters[1]
    assert letter2.insurer_name == "UnitedHealth"
    assert letter2.policy_id == "UH-990-GOLD"
    
    content2 = letter2.letter_content
    assert "Prior Authorization Department, UnitedHealth" in content2
    # In UnitedHealth, Priya Sen's member ID is 12345-02
    assert "Member ID:** 12345-02" in content2
    
    # Verify pre-auth rules resolved under UH-990-GOLD
    # CPT 29881 does NOT require preauth on UnitedHealth (No (Covered))
    assert "| `29881` | Arthroscopy knee meniscus repair | ₹8,900.00 | No (Covered) |" in content2


def test_generate_letters_single_coverage(preauth_service, mock_insurance_service):
    """Verify that only one letter is generated when the patient has single-insurer coverage."""
    state = SharedWorkflowState(claim_id="TEST-200", member_id="98765")
    
    state.primary_policy = mock_insurance_service._policies["BS-120-BLUE"]
    state.secondary_policy = None
    
    state.coding_result = CodingResult(
        diagnoses=[
            Diagnosis(code="M23.231", description="Tear of meniscus", confidence=0.98)
        ],
        procedures=[
            Procedure(code="29881", description="Arthroscopy knee meniscus repair", confidence=0.97)
        ]
    )

    response = preauth_service.generate_letters(state)

    assert len(response.letters) == 1
    assert response.letters[0].insurer_name == "BlueShield Cross"

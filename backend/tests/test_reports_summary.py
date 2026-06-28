import pytest
from fastapi.testclient import TestClient
from app.core.app import get_app
from app.api.v1.endpoints.analysis import jobs_db
from app.core.adk import SharedWorkflowState
from app.schemas.analysis import JobStatus
from app.schemas.medical_coding import CodingResult
from app.schemas.finance_engine import FinancialReport, CostSummary, PatientResponsibility, FinancialBreakdown
from app.schemas.cob_engine import COBDecision
from datetime import datetime

@pytest.fixture
def client():
    app = get_app()
    return TestClient(app)

def test_reports_summary_fallback(client):
    # Setup standard success state
    from app.schemas.insurance_engine import InsurancePolicy, Deductible, Coinsurance, Member
    
    state = SharedWorkflowState(claim_id="CLAIM-MOCK", member_id="98765")
    state.workflow_status = "success"
    from app.schemas.medical_coding import Procedure, Diagnosis
    from app.schemas.insurance_engine import CoverageRule
    state.coding_result = CodingResult(
        diagnoses=[Diagnosis(code="M23.231", description="Meniscus tear", confidence=0.95)],
        procedures=[Procedure(code="29881", description="Arthroscopy knee", confidence=0.95)]
    )
    state.primary_policy = InsurancePolicy(
        policy_id="BS-120-BLUE",
        provider_name="BlueShield Cross",
        group_number="BS120",
        deductible=Deductible(individual=500.0, family=1000.0, remaining_individual=200.0, remaining_family=500.0),
        coinsurance=Coinsurance(rate=0.20),
        out_of_pocket_max=3000.0,
        remaining_out_of_pocket_max=1200.0,
        members=[
            Member(
                member_id="98765",
                first_name="Priya",
                last_name="Sen",
                role="subscriber",
                relationship_to_subscriber="self",
                date_of_birth="1985-04-12"
            )
        ],
        coverage_rules=[
            CoverageRule(cpt_code="29881", is_covered=True, requires_preauth=True)
        ]
    )
    state.cob_decision = COBDecision(
        claim_id="CLAIM-MOCK",
        patient_name="Priya Sen",
        primary_policy_id="BS-120-BLUE",
        primary_provider="BlueShield Cross",
        lines_coverage=[],
        total_billed=0.0,
        total_primary_paid=0.0,
        total_secondary_paid=0.0,
        total_patient_responsibility=0.0
    )
    state.financial_report = FinancialReport(
        report_id="FIN-MOCK",
        claim_id="CLAIM-MOCK",
        patient_name="Priya Sen",
        generated_at=datetime.utcnow().isoformat() + "Z",
        primary_policy_id="BS-120-BLUE",
        breakdown=FinancialBreakdown(
            allocations=[],
            patient_responsibility=PatientResponsibility(
                total_deductible=0.0,
                total_coinsurance=0.0,
                total_responsibility=0.0,
                explanation_notes="Mock notes"
            ),
            summary=CostSummary(
                total_billed=0.0,
                total_primary_paid=0.0,
                total_secondary_paid=0.0,
                total_insurer_paid=0.0,
                total_patient_responsibility=0.0,
                total_savings=0.0
            )
        )
    )
    from app.core.adk import TraceEntry
    state.trace = [
        TraceEntry(
            agent_name="IntakeAgent",
            status="success",
            message="Intake completed successfully.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    ]

    jobs_db["mock-job-id"] = {
        "job_id": "mock-job-id",
        "status": JobStatus.COMPLETED,
        "progress_percent": 100,
        "message": "Completed",
        "created_at": datetime.utcnow(),
        "completed_at": datetime.utcnow(),
        "error_details": None,
        "state": state
    }

    response = client.get("/api/v1/reports/summary?job_id=mock-job-id")
    assert response.status_code == 200
    data = response.json()
    
    # Assert primary fields
    assert "job_id" in data
    assert data["job_id"] == "mock-job-id"
    assert "patient_name" in data
    assert "financial_summary" in data
    assert "preauth_letters" in data
    
    # Assert expanded dashboard fields
    assert "workflow_summary" in data
    assert "trace" in data
    assert "coding_result" in data
    assert "warnings" in data
    assert "letters" in data
    
    # Validate trace entries
    trace = data["trace"]
    assert len(trace) > 0
    for entry in trace:
        assert "agent_name" in entry
        assert "status" in entry
        assert "message" in entry
        assert "timestamp" in entry
        
    # Validate preauth letters
    letters = data["letters"]
    assert len(letters) > 0
    for letter in letters:
        assert "insurer_name" in letter
        assert "policy_id" in letter
        assert "patient_name" in letter
        assert "letter_content" in letter
        assert "generated_at" in letter

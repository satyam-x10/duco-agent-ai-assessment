import pytest
from fastapi.testclient import TestClient
from app.core.app import get_app

@pytest.fixture
def client():
    app = get_app()
    return TestClient(app)

def test_reports_summary_fallback(client):
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

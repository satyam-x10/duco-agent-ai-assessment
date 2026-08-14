from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.v1.endpoints.analysis import jobs_db
from app.core.adk import SharedWorkflowState
from app.core.app import get_app
from app.schemas.analysis import JobStatus


def _awaiting_job(job_id: str) -> SharedWorkflowState:
    state = SharedWorkflowState(claim_id="APPROVAL-1", member_id="98765")
    state.workflow_status = "success"
    state.requires_human_approval = True
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": JobStatus.AWAITING_APPROVAL,
        "progress_percent": 99,
        "message": "Awaiting approval",
        "created_at": datetime.utcnow(),
        "completed_at": datetime.utcnow(),
        "error_details": None,
        "state": state,
    }
    return state


def test_reports_are_gated_until_clinician_approval():
    jobs_db.clear()
    state = _awaiting_job("approval-gate")
    client = TestClient(get_app())

    blocked = client.get("/api/v1/reports/summary?job_id=approval-gate")
    assert blocked.status_code == 409
    assert state.artifacts_finalized is False

    approved = client.post("/api/v1/analysis/approve?job_id=approval-gate")
    assert approved.status_code == 200
    assert state.human_approved is True
    assert state.artifacts_finalized is True
    assert state.audio_briefing is not None


def test_rejection_reuses_existing_state_for_the_correction_run():
    jobs_db.clear()
    state = _awaiting_job("approval-reject")
    client = TestClient(get_app())
    scheduled = object()

    with patch(
        "app.api.v1.endpoints.analysis._run_orchestration",
        MagicMock(return_value=scheduled),
    ) as rerun, patch("app.api.v1.endpoints.analysis.asyncio.create_task") as create_task:
        response = client.post("/api/v1/analysis/reject?job_id=approval-reject")

    assert response.status_code == 200
    rerun.assert_called_once_with("approval-reject", existing_state=state)
    create_task.assert_called_once_with(scheduled)
    assert jobs_db["approval-reject"]["state"] is state
    assert state.artifacts_finalized is False
    assert any(entry.agent_name == "ClinicianAuditor" and entry.status == "retry" for entry in state.trace)

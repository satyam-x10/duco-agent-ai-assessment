from datetime import datetime
from fastapi import APIRouter
from app.schemas.reports import (
    ReportSummaryResponse,
    FinancialSummary,
    LetterMetadata,
    AudioMetadata,
)

router = APIRouter()


@router.get("/summary", response_model=ReportSummaryResponse)
async def get_report_summary(job_id: str = "mock-job-id"):
    """
    Retrieves the finalized Coordination of Benefits (COB) report.
    Returns financial breakdowns, pre-authorization document targets, and audio assets.
    """
    return ReportSummaryResponse(
        job_id=job_id,
        patient_name="Priya Patel",
        financial_summary=FinancialSummary(
            total_billed=1250.00,
            primary_paid=800.00,
            secondary_paid=300.00,
            patient_responsibility=150.00,
            currency="USD"
        ),
        preauth_letters=[
            LetterMetadata(
                insurer_name="BlueShield Cross",
                generated_at=datetime.utcnow(),
                download_url="/api/v1/reports/download/letter_blueshield.pdf",
                status="generated"
            ),
            LetterMetadata(
                insurer_name="UnitedHealth",
                generated_at=datetime.utcnow(),
                download_url="/api/v1/reports/download/letter_united.pdf",
                status="generated"
            )
        ],
        audio_summary=AudioMetadata(
            duration_seconds=78.5,
            generated_at=datetime.utcnow(),
            download_url="/api/v1/reports/download/audio_summary.mp3"
        ),
        completed_at=datetime.utcnow()
    )

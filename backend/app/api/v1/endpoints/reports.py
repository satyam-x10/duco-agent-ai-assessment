import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from app.schemas.reports import (
    ReportSummaryResponse,
    FinancialSummary,
    LetterMetadata,
    AudioMetadata,
    TraceEntrySchema,
    ClaimLineCoverageSchema
)
from app.core.adk import SharedWorkflowState
from app.api.v1.endpoints.analysis import jobs_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=ReportSummaryResponse)
async def get_report_summary(job_id: str):
    """
    Retrieves the finalized Coordination of Benefits (COB) report.

    Only returns a report when the workflow_status is 'success'.
    If the pipeline failed, returns a structured 424 error with the failing agent and reason.
    If the job does not exist, returns 404.
    """
    # Validate job exists
    if job_id not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found. Please run /analysis/start first."
        )

    job = jobs_db[job_id]
    job_status = job.get("status")

    # Job still running
    if job_status in ("pending", "processing"):
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Analysis is still in progress. Poll /analysis/status/{job_id} and retry when completed."
        )

    if job_status == "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Clinician approval is required before reports or artifacts can be finalized.",
        )

    # Job failed — return structured error
    if job_status == "failed":
        failed_agent = job.get("failed_agent", "Unknown")
        error_details = job.get("error_details", "An unspecified error occurred in the pipeline.")
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "status": "failed",
                "step": failed_agent,
                "message": error_details,
            }
        )

    # Retrieve real workflow state
    state: Optional[SharedWorkflowState] = job.get("state")
    if not state or state.workflow_status != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow state is missing or incomplete despite job completion. This is an internal error."
        )
    if not state.artifacts_finalized:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow artifacts have not been finalized.",
        )

    # Validate required pipeline outputs exist
    if not state.financial_report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Financial report is missing from completed workflow state."
        )
    if not state.cob_decision:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="COB decision is missing from completed workflow state."
        )

    # 1. Financial summary from real pipeline output
    fin = state.financial_report.breakdown.summary
    total_billed = fin.total_billed
    primary_paid = fin.total_primary_paid
    secondary_paid = fin.total_secondary_paid
    patient_responsibility = fin.total_patient_responsibility

    patient_name = state.financial_report.patient_name or state.cob_decision.patient_name or "Unknown Patient"

    # 2. Generate pre-authorization letters from real state
    from services.preauth import PreAuthorizationService
    preauth_service = PreAuthorizationService()
    preauth_res = preauth_service.generate_letters(state)

    preauth_letters = []
    for letter in preauth_res.letters:
        download_url = f"/api/v1/reports/download/letter_{letter.insurer_name.lower().replace(' ', '_')}.pdf"
        preauth_letters.append(
            LetterMetadata(
                insurer_name=letter.insurer_name,
                generated_at=datetime.utcnow(),
                download_url=download_url,
                status="generated"
            )
        )

    # 3. Workflow summary checklist (all True since workflow_status == success)
    workflow_summary = {
        "Upload completed": len(state.processed_documents) > 0,
        "Documents processed": any(t.agent_name == "DocIntelAgent" and t.status == "success" for t in state.trace),
        "Medical codes inferred": state.coding_result is not None,
        "Insurance policies resolved": state.primary_policy is not None,
        "COB completed": state.cob_decision is not None,
        "Finance completed": state.financial_report is not None,
    }

    # 4. Map trace entries
    trace_schemas = [
        TraceEntrySchema(
            agent_name=t.agent_name,
            status=t.status,
            message=t.message,
            timestamp=t.timestamp
        )
        for t in state.trace
    ]

    # 5. Generate audio briefing from real state
    from app.dependencies.audio import get_audio_briefing_service
    briefing_service = get_audio_briefing_service()
    briefing_res = briefing_service.generate_briefing(state)
    state.audio_briefing = briefing_res.briefing

    # 6. Letter download URLs with job_id parameter
    preauth_letters = []
    for letter in preauth_res.letters:
        download_url = f"/api/v1/reports/download/letter_{letter.insurer_name.lower().replace(' ', '_')}.pdf?job_id={job_id}"
        preauth_letters.append(
            LetterMetadata(
                insurer_name=letter.insurer_name,
                generated_at=datetime.utcnow(),
                download_url=download_url,
                status="generated"
            )
        )

    # 7. Map per-procedure COB line-level coverage decisions for frontend transparency
    cpt_description_fallback = {
        "97161": "Physical Therapy Evaluation",
        "97110": "Therapeutic Exercises",
        "73721": "MRI Joint Lower Extremity",
        "29881": "Arthroscopy knee meniscus repair",
        "29888": "Arthroscopically aided ACL reconstruction",
        "97140": "Manual Therapy Techniques",
        "97112": "Neuromuscular Reeducation",
        "29882": "Arthroscopy knee meniscus suture"
    }

    cob_lines = []
    if state.cob_decision and state.cob_decision.lines_coverage:
        for line in state.cob_decision.lines_coverage:
            # Find description of this CPT code from coding_result or fallback dictionary
            description = ""
            if state.coding_result and state.coding_result.procedures:
                for proc in state.coding_result.procedures:
                    if proc.code == line.cpt_code:
                        description = proc.description
                        break
            if not description:
                description = cpt_description_fallback.get(line.cpt_code, "Unrecognized Medical Procedure")

            cob_lines.append(
                ClaimLineCoverageSchema(
                    cpt_code=line.cpt_code,
                    description=description,
                    patient_name=line.patient_name,
                    member_id=line.member_id,
                    source_document=line.source_document,
                    billed_amount=line.billed_amount,
                    is_primary_covered=line.primary_coverage.is_covered,
                    primary_deductible=line.primary_coverage.deductible_applied,
                    primary_coinsurance=line.primary_coverage.coinsurance_amount,
                    primary_paid=line.primary_coverage.primary_paid,
                    is_secondary_covered=line.secondary_coverage.is_covered,
                    secondary_deductible=line.secondary_coverage.deductible_applied,
                    secondary_paid=line.secondary_coverage.secondary_paid,
                    patient_responsibility=line.remaining_balance.patient_responsibility,
                    notes=line.remaining_balance.notes or "",
                )
            )

    return ReportSummaryResponse(
        job_id=job_id,
        patient_name=patient_name,
        financial_summary=FinancialSummary(
            total_billed=total_billed,
            primary_paid=primary_paid,
            secondary_paid=secondary_paid,
            patient_responsibility=patient_responsibility,
            primary_provider=state.cob_decision.primary_provider,
            secondary_provider=state.cob_decision.secondary_provider,
            currency="INR"
        ),
        preauth_letters=preauth_letters,
        audio_summary=AudioMetadata(
            duration_seconds=briefing_res.briefing.estimated_duration_seconds,
            generated_at=datetime.utcnow(),
            download_url=f"/api/v1/reports/download/audio_summary.mp3?job_id={job_id}"
        ),
        completed_at=job.get("completed_at") or datetime.utcnow(),
        workflow_summary=workflow_summary,
        trace=trace_schemas,
        coding_result=state.coding_result,
        warnings=state.warnings,
        letters=preauth_res.letters,
        audio_briefing=briefing_res.briefing,
        requires_human_approval=getattr(state, "requires_human_approval", False),
        human_approved=getattr(state, "human_approved", False),
        cob_lines=cob_lines,
        patient_claims=state.cob_decision.patient_claims,
    )


def generate_letter_pdf(text: str) -> bytes:
    """Render a readable, multipage clinician-review PDF from the draft markdown."""
    import html
    import io
    import re

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Prior Authorization Request - Draft for Clinician Review",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DraftTitle", parent=styles["Title"], fontSize=15, leading=18, textColor=colors.HexColor("#16324F"), alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=11, leading=14, textColor=colors.HexColor("#1D4E89"), spaceBefore=8, spaceAfter=4, keepWithNext=True))
    styles.add(ParagraphStyle(name="Notice", parent=styles["BodyText"], fontSize=8.5, leading=12, backColor=colors.HexColor("#FFF4CC"), borderColor=colors.HexColor("#D8A800"), borderWidth=0.5, borderPadding=7, spaceAfter=8))
    body_style = ParagraphStyle("LetterBody", parent=styles["BodyText"], fontSize=8.7, leading=12, spaceAfter=2.5)

    def inline(value: str) -> str:
        value = value.replace("₹", "INR ")
        value = html.escape(value)
        value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
        value = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", value)
        return value

    story = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index].strip()
        if not raw:
            story.append(Spacer(1, 0.8 * mm))
            index += 1
            continue
        if raw.startswith("| "):
            table_rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[: -]+", cell) for cell in cells):
                    table_rows.append([Paragraph(inline(cell), body_style) for cell in cells])
                index += 1
            if table_rows:
                col_widths = [20 * mm, 62 * mm, 38 * mm, 38 * mm][: len(table_rows[0])]
                table = Table(table_rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1F8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#16324F")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7C4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                story.append(table)
            continue
        if raw.startswith("# "):
            story.append(Paragraph(inline(raw[2:]), styles["DraftTitle"]))
        elif raw.startswith("## "):
            story.append(Paragraph(inline(raw[3:]), styles["Section"]))
        elif raw.startswith("> "):
            story.append(Paragraph(inline(raw[2:]), styles["Notice"]))
        elif raw.startswith("- "):
            story.append(Paragraph(f"- {inline(raw[2:])}", body_style))
        else:
            story.append(Paragraph(inline(raw.rstrip("  ")), body_style))
        index += 1

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#607080"))
        canvas.drawString(18 * mm, 10 * mm, "DRAFT - CLINICIAN REVIEW REQUIRED")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


generate_minimal_pdf = generate_letter_pdf

from fastapi.responses import Response

@router.get("/download/letter_{insurer_name}.pdf")
async def download_letter(insurer_name: str, job_id: str):
    """
    Generates and downloads a valid PDF of the pre-authorization letter for the specified insurer.
    """
    if job_id not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found."
        )
    
    job = jobs_db[job_id]
    state = job.get("state")
    if job.get("status") != "completed" or not state or state.workflow_status != "success" or not state.artifacts_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow state is not ready or failed."
        )
        
    from services.preauth import PreAuthorizationService
    preauth_service = PreAuthorizationService()
    preauth_res = preauth_service.generate_letters(state)
    
    # Find matching letter
    target_insurer = insurer_name.replace("_", " ").lower()
    matching_letter = None
    for letter in preauth_res.letters:
        if letter.insurer_name.lower() == target_insurer:
            matching_letter = letter.letter_content
            break
            
    if not matching_letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pre-authorization letter for insurer '{insurer_name}' not found."
        )
        
    # Generate minimal valid PDF from the text
    pdf_bytes = generate_minimal_pdf(matching_letter)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=preauth_letter_{insurer_name}.pdf"
        }
    )

@router.get("/download/cost_flow.svg")
async def download_cost_flow(job_id: str):
    """
    Generates and downloads a dynamic SVG waterfall chart representing the exact live COB decision.
    """
    if job_id not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found."
        )

    job = jobs_db[job_id]
    state = job.get("state")
    if job.get("status") != "completed" or not state or state.workflow_status != "success" or not state.artifacts_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow state is not ready or failed."
        )

    from services.cost_flow import CostFlowVisualizerService
    
    fin = state.financial_report.breakdown.summary if state.financial_report else None
    total_billed = fin.total_billed if fin else 0.0
    primary_paid = fin.total_primary_paid if fin else 0.0
    secondary_paid = fin.total_secondary_paid if fin else 0.0
    patient_resp = fin.total_patient_responsibility if fin else 0.0
    
    lines_summary = []
    if state.cob_decision and state.cob_decision.lines_coverage:
        for line in state.cob_decision.lines_coverage:
            lines_summary.append({
                "cpt_code": line.cpt_code,
                "billed_amount": line.billed_amount,
            })
    
    svg_content = CostFlowVisualizerService.generate_svg(
        billed=total_billed,
        primary_paid=primary_paid,
        secondary_paid=secondary_paid,
        patient_responsibility=patient_resp,
        primary_payer=state.cob_decision.primary_provider if state.cob_decision else "Primary Payer",
        secondary_payer=state.cob_decision.secondary_provider if state.cob_decision else None,
        patient_name=state.cob_decision.patient_name if state.cob_decision else "Patient",
        lines_summary=lines_summary,
    )

    return Response(
        content=svg_content.encode("utf-8"),
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": "attachment; filename=dual_coverage_cost_flow.svg"
        }
    )


@router.get("/download/audio_summary.mp3")
async def download_audio_summary(job_id: str):
    """
    Streams an audio summary MP3 file containing the narration briefing.
    Raises an explicit HTTP 503 error if the text-to-speech engine fails rather than returning silent frames.
    """
    if job_id not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found."
        )
        
    job = jobs_db[job_id]
    state = job.get("state")
    if job.get("status") != "completed" or not state or not state.artifacts_finalized:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audio is unavailable until the workflow is finalized.",
        )
    
    if not state.audio_briefing or not state.audio_briefing.full_narration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio briefing narration text is missing from finalized state."
        )

    narration_text = state.audio_briefing.full_narration
        
    try:
        from gtts import gTTS
        import io
        tts = gTTS(text=narration_text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        mp3_bytes = fp.getvalue()
    except Exception as e:
        logger.error(f"Failed to generate TTS MP3 via online service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Text-to-speech audio service is currently unavailable: {str(e)}. Please review the text transcript."
        )
    
    return Response(
        content=mp3_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "attachment; filename=audio_summary.mp3"
        }
    )

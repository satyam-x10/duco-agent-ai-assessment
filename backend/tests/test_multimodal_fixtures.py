from pathlib import Path

import pytest

from app.schemas.intake import DocumentType
from services.document_intelligence import ImageProcessor, PDFProcessor


SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_inputs"


def test_real_multimodal_fixtures_are_present():
    expected = {
        "priya_pt_invoice.png",
        "aarav_surgeon_estimate.png",
        "aarav_mri_report.pdf",
        "aarav_no_tear_negative.pdf",
    }
    assert expected.issubset({path.name for path in SAMPLE_DIR.iterdir()})


@pytest.mark.asyncio
async def test_real_pdf_extracts_patient_and_clinical_findings():
    processed = await PDFProcessor().process(
        SAMPLE_DIR / "aarav_mri_report.pdf",
        DocumentType.AARAV_MRI_REPORT,
        ocr_engine="library",
    )

    assert processed.metadata["parser"] == "PDFProcessor"
    assert processed.page_count == 3
    assert processed.facts.patient_name == "Aarav Sen"
    assert {"S83.511A", "M23.231"}.issubset(processed.facts.diagnosis_codes)
    assert "Complete tear of the anterior cruciate ligament" in processed.extracted_text


@pytest.mark.asyncio
async def test_real_local_image_ocr_extracts_grounded_surgical_charges():
    processed = await ImageProcessor().process(
        SAMPLE_DIR / "aarav_surgeon_estimate.png",
        DocumentType.SURGEON_ESTIMATE,
        ocr_engine="library",
    )

    assert processed.facts.patient_name == "Aarav Sen"
    charges = {line.cpt_code: line.billed_amount for line in processed.facts.line_items}
    assert charges == {"29888": 350000.0, "29881": 100000.0}
    assert all(line.amount_source == "explicit_line" for line in processed.facts.line_items)


@pytest.mark.asyncio
async def test_real_local_image_ocr_marks_total_only_charge_allocation_for_review():
    processed = await ImageProcessor().process(
        SAMPLE_DIR / "priya_pt_invoice.png",
        DocumentType.PRIYA_PT_INVOICE,
        ocr_engine="library",
    )

    assert processed.facts.patient_name == "Priya Sen"
    assert processed.facts.total_billed == 30000.0
    assert round(sum(line.billed_amount for line in processed.facts.line_items), 2) == 30000.0
    assert {line.cpt_code for line in processed.facts.line_items} == {"97161", "97110", "97140", "97112"}
    assert all(
        line.amount_source == "allocated_from_document_total"
        for line in processed.facts.line_items
    )

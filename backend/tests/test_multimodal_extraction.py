import json
import pytest
from pathlib import Path
from app.schemas.intake import DocumentType
from services.document_intelligence import DocumentIntelligenceService, DocumentProcessorFactory
from services.document_facts import extract_document_facts

SAMPLE_INPUTS_DIR = Path(__file__).resolve().parent.parent / "sample_inputs"
GROUND_TRUTH_PATH = SAMPLE_INPUTS_DIR / "ground_truth.json"


@pytest.fixture
def doc_intel_service():
    factory = DocumentProcessorFactory()
    return DocumentIntelligenceService(factory)


@pytest.fixture
def ground_truth():
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_text_processor_priya_pt_invoice_sample(doc_intel_service, ground_truth):
    """Verifies that Priya PT invoice text parses correctly and matches ground truth codes."""
    sample_file = SAMPLE_INPUTS_DIR / "priya_pt_invoice_sample.txt"
    if not sample_file.exists():
        pytest.skip("Sample file not found.")

    doc = await doc_intel_service.process_document(
        file_path=sample_file,
        document_type=DocumentType.PRIYA_PT_INVOICE,
        strategy="standard"
    )

    assert doc.extracted_text is not None
    assert doc.confidence >= 0.90
    assert doc.facts.patient_name == "Priya Sen"
    assert doc.facts.member_id == "98765"
    assert "M54.50" in doc.facts.diagnosis_codes
    line_cpts = {line.cpt_code for line in doc.facts.line_items}
    assert "97161" in line_cpts
    assert "97110" in line_cpts


@pytest.mark.asyncio
async def test_text_processor_aarav_mri_report_sample(doc_intel_service, ground_truth):
    """Verifies that Aarav MRI report sample parses and extracts meniscus diagnosis."""
    sample_file = SAMPLE_INPUTS_DIR / "aarav_mri_report_sample.txt"
    if not sample_file.exists():
        pytest.skip("Sample file not found.")

    doc = await doc_intel_service.process_document(
        file_path=sample_file,
        document_type=DocumentType.AARAV_MRI_REPORT,
        strategy="standard"
    )

    assert doc.extracted_text is not None
    assert "Aarav" in doc.facts.patient_name
    assert "M23.231" in doc.facts.diagnosis_codes
    line_cpts = {line.cpt_code for line in doc.facts.line_items}
    assert "73721" in line_cpts


@pytest.mark.asyncio
async def test_text_processor_aarav_surgeon_estimate_sample(doc_intel_service, ground_truth):
    """Verifies that surgeon estimate parses provider details and surgical CPT lines."""
    sample_file = SAMPLE_INPUTS_DIR / "aarav_surgeon_estimate_sample.txt"
    if not sample_file.exists():
        pytest.skip("Sample file not found.")

    doc = await doc_intel_service.process_document(
        file_path=sample_file,
        document_type=DocumentType.SURGEON_ESTIMATE,
        strategy="standard"
    )

    assert doc.extracted_text is not None
    assert "Dr. Meera Shah" in (doc.facts.provider.name or "")
    line_cpts = {line.cpt_code for line in doc.facts.line_items}
    assert "29881" in line_cpts
    assert "29888" in line_cpts


@pytest.mark.asyncio
async def test_pdf_processor_aarav_mri_pdf(doc_intel_service):
    """Verifies that PDFProcessor extracts text directly from Aarav MRI PDF."""
    pdf_file = SAMPLE_INPUTS_DIR / "aarav_mri_report.pdf"
    if not pdf_file.exists():
        pytest.skip("PDF file not found.")

    doc = await doc_intel_service.process_document(
        file_path=pdf_file,
        document_type=DocumentType.AARAV_MRI_REPORT,
        strategy="standard"
    )

    assert doc.extracted_text is not None
    assert len(doc.extracted_text) > 20
    assert doc.confidence >= 0.85

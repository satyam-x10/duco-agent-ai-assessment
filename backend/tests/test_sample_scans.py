import json
from pathlib import Path
import pytest
from app.schemas.intake import DocumentType
from services.document_facts import extract_document_facts
from services.document_intelligence import PDFProcessor, ImageProcessor

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_inputs"


def test_committed_text_sample_documents_match_ground_truth():
    """Verify that deterministic facts extractor parses committed text files against ground_truth.json."""
    gt_file = SAMPLE_DIR / "ground_truth.json"
    assert gt_file.exists(), "ground_truth.json must be committed"

    with open(gt_file, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    for filename, expected in ground_truth.get("documents", {}).items():
        if not filename.endswith(".txt"):
            continue
        sample_path = SAMPLE_DIR / filename
        assert sample_path.exists(), f"Sample file {filename} must exist"

        text = sample_path.read_text(encoding="utf-8")
        facts = extract_document_facts(text)

        # Assert patient identity
        assert facts.patient_name == expected["patient_name"]
        assert facts.member_id == expected["member_id"]
        assert facts.date_of_birth == expected["date_of_birth"]

        # Assert extracted diagnoses
        if "diagnosis_codes" in expected:
            for d in expected["diagnosis_codes"]:
                assert d in facts.diagnosis_codes

        # Assert extracted line items and billed amounts
        if "line_items" in expected:
            extracted_lines = {li.cpt_code: li.billed_amount for li in facts.line_items}
            for exp_li in expected["line_items"]:
                cpt = exp_li["cpt_code"]
                assert cpt in extracted_lines
                assert extracted_lines[cpt] == exp_li["billed_amount"]


@pytest.mark.asyncio
async def test_committed_binary_fixtures_match_ground_truth():
    """Verify that multimodal OCR processors extract grounded facts matching ground_truth.json for all binary fixtures."""
    gt_file = SAMPLE_DIR / "ground_truth.json"
    assert gt_file.exists()

    with open(gt_file, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    pdf_processor = PDFProcessor()
    img_processor = ImageProcessor()

    type_mapping = {
        "aarav_mri_report.pdf": DocumentType.AARAV_MRI_REPORT,
        "aarav_no_tear_negative.pdf": DocumentType.AARAV_MRI_REPORT,
        "aarav_surgeon_estimate.png": DocumentType.SURGEON_ESTIMATE,
        "priya_pt_invoice.png": DocumentType.PRIYA_PT_INVOICE,
    }

    for filename, doc_type in type_mapping.items():
        expected = ground_truth["documents"][filename]
        sample_path = SAMPLE_DIR / filename
        assert sample_path.exists()

        if filename.endswith(".pdf"):
            processed = await pdf_processor.process(sample_path, doc_type, ocr_engine="library")
        else:
            processed = await img_processor.process(sample_path, doc_type, ocr_engine="library")

        facts = processed.facts
        assert facts.patient_name == expected["patient_name"]

        if "date_of_birth" in expected and facts.date_of_birth:
            assert facts.date_of_birth == expected["date_of_birth"]

        if "diagnosis_codes" in expected:
            for d in expected["diagnosis_codes"]:
                assert d in facts.diagnosis_codes

        if "line_items" in expected:
            extracted_lines = {li.cpt_code: li.billed_amount for li in facts.line_items}
            for exp_li in expected["line_items"]:
                cpt = exp_li["cpt_code"]
                assert cpt in extracted_lines
                assert extracted_lines[cpt] == exp_li["billed_amount"]

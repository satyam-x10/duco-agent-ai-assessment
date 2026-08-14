import json
from pathlib import Path
from services.document_facts import extract_document_facts

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_inputs"


def test_committed_sample_documents_match_ground_truth():
    """Verify that deterministic facts extractor parses committed sample files against ground_truth.json."""
    gt_file = SAMPLE_DIR / "ground_truth.json"
    assert gt_file.exists(), "ground_truth.json must be committed"

    with open(gt_file, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    for filename, expected in ground_truth.get("documents", {}).items():
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
